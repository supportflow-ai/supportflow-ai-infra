"""Kiểm thử script thật với mc giả; không cần Docker hoặc Python package ngoài."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SHELL = os.environ.get("TEST_SH") or shutil.which("sh")


class MinioInitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SHELL:
            raise RuntimeError("Cần POSIX sh để kiểm thử script thật.")
        probe = subprocess.run([SHELL, "-c", "exit 0"], capture_output=True, timeout=10)
        if probe.returncode != 0:
            raise RuntimeError("POSIX sh không chạy được trong môi trường này; chưa thể kiểm chứng script.")

    def setUp(self):
        self.assertIsNotNone(SHELL, "Cần POSIX sh (Windows: đặt TEST_SH tới Git sh.exe).")
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tmp")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.assertTrue(self.work.resolve().is_relative_to((ROOT / "tmp").resolve()))
        self.mc = self.work / "mc"
        self.mc.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$MC_LOG"
case "$1" in
  alias) if [ "${FAIL_ALIAS:-0}" = 1 ]; then echo "$MINIO_ROOT_PASSWORD" >&2; exit 7; fi ;;
  mb) if [ "${FAIL_BUCKET:-0}" = 1 ]; then echo "$MINIO_ROOT_PASSWORD" >&2; exit 8; fi ;;
esac
if [ "$1 $2 $3" = "admin policy create" ]; then cat "$6" > "$MC_POLICY"; fi
''', encoding="utf-8", newline="\n")
        self.mc.chmod(0o755)
        self.env = dict(os.environ, MINIO_ROOT_USER="custom_user",
                        MINIO_ROOT_PASSWORD="test_password_must_not_be_logged",
                        MINIO_DEFAULT_BUCKET="custom-bucket", MINIO_ENDPOINT="http://custom:9000",
                        MINIO_MC_BINARY=self.mc.as_posix(), MC_LOG=(self.work / "calls").as_posix(),
                        MINIO_INIT_MAX_ATTEMPTS="2", MINIO_INIT_RETRY_DELAY_SECONDS="0",
                        FAIL_ALIAS="0", FAIL_BUCKET="0", MINIO_APP_ACCESS_KEY="",
                        MINIO_APP_SECRET_KEY="", MINIO_LIFECYCLE_FILE="",
                        MC_POLICY=(self.work / "policy.json").as_posix())

    def run_script(self):
        return subprocess.run([SHELL, (ROOT / "scripts/init_minio_buckets.sh").as_posix()],
                              env=self.env, capture_output=True, text=True,
                              encoding="utf-8", timeout=10)

    def calls(self):
        p = self.work / "calls"
        return p.read_text(encoding="utf-8").splitlines() if p.exists() else []

    def test_custom_credentials_and_bucket(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            "alias set local http://custom:9000 custom_user test_password_must_not_be_logged",
            "mb --ignore-existing local/custom-bucket"])

    def test_repeated_initialization_uses_idempotent_bucket_creation(self):
        for _ in range(2):
            self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(self.calls().count("mb --ignore-existing local/custom-bucket"), 2)

    def test_authentication_failure_is_bounded_and_does_not_create_bucket(self):
        self.env["FAIL_ALIAS"] = "1"
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.calls()), 2)
        self.assertTrue(all(call.startswith("alias ") for call in self.calls()))
        self.assertNotIn(self.env["MINIO_ROOT_PASSWORD"], result.stdout + result.stderr)

    def test_bucket_failure_is_not_reported_as_success(self):
        self.env["FAIL_BUCKET"] = "1"
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("hoàn tất thành công", result.stdout)
        self.assertNotIn(self.env["MINIO_ROOT_PASSWORD"], result.stdout + result.stderr)

    def test_missing_or_empty_credentials_fail_before_mc(self):
        for key in ("MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"):
            with self.subTest(key=key):
                value = self.env.pop(key)
                self.assertNotEqual(self.run_script().returncode, 0)
                self.env[key] = ""
                self.assertNotEqual(self.run_script().returncode, 0)
                self.env[key] = value
        self.assertEqual(self.calls(), [])

    def test_invalid_retry_configuration_fails_before_mc(self):
        for key, value in (("MINIO_INIT_MAX_ATTEMPTS", "0"),
                           ("MINIO_INIT_MAX_ATTEMPTS", "abc"),
                           ("MINIO_INIT_RETRY_DELAY_SECONDS", "-1")):
            with self.subTest(key=key, value=value):
                previous = self.env[key]
                self.env[key] = value
                self.assertNotEqual(self.run_script().returncode, 0)
                self.env[key] = previous
        self.assertEqual(self.calls(), [])

    def test_application_policy_is_limited_to_configured_bucket(self):
        self.env.update(MINIO_APP_ACCESS_KEY="app-key", MINIO_APP_SECRET_KEY="synthetic-app-secret")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        policy = json.loads((self.work / "policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["Statement"][0]["Resource"], ["arn:aws:s3:::custom-bucket"])
        self.assertEqual(policy["Statement"][1]["Resource"], [
            "arn:aws:s3:::custom-bucket/uploads/pending/*", "arn:aws:s3:::custom-bucket/tickets/*"])
        self.assertNotIn("s3:*", json.dumps(policy))
        self.assertNotIn(self.env["MINIO_APP_SECRET_KEY"], result.stdout + result.stderr)
        self.assertTrue(any(call.startswith("admin policy attach local custom-bucket-app --user app-key") for call in self.calls()))

    def test_incomplete_app_credentials_fail_before_any_storage_change(self):
        self.env["MINIO_APP_ACCESS_KEY"] = "app-key"
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_pending_lifecycle_file_is_imported_for_dedicated_bucket(self):
        self.env["MINIO_LIFECYCLE_FILE"] = (ROOT / "storage/pending-upload-lifecycle.json").as_posix()
        self.assertEqual(self.run_script().returncode, 0)
        self.assertIn("ilm import local/custom-bucket", self.calls())


class ComposeConfigTests(unittest.TestCase):
    def test_both_compose_files_pass_custom_environment_to_init(self):
        for filename, env_file in (("docker-compose.yml", "example.env"),
                                   ("deploy/compose.system.yml", "deploy/example.env")):
            with self.subTest(compose=filename):
                env = dict(os.environ, MINIO_ROOT_USER="custom_user",
                           MINIO_ROOT_PASSWORD="custom_test_password",
                           MINIO_DEFAULT_BUCKET="custom-test-bucket")
                result = subprocess.run(["docker", "compose", "--env-file", env_file,
                                         "-f", filename, "config", "--format", "json"],
                                        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                services = json.loads(result.stdout)["services"]
                init = services["minio-init"]
                for key in ("MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "MINIO_DEFAULT_BUCKET"):
                    self.assertEqual(init["environment"][key], env[key])
                self.assertEqual(init["entrypoint"], ["/bin/sh", "/opt/supportflow/init_minio_buckets.sh"])
                mount = next(v for v in init["volumes"] if v["target"] == "/opt/supportflow/init_minio_buckets.sh")
                self.assertTrue(mount["read_only"])
                self.assertTrue(Path(mount["source"]).is_file())
                for name in ("api-1", "api-2", "worker"):
                    if name in services:
                        self.assertEqual(services[name]["depends_on"]["minio-init"]["condition"],
                                         "service_completed_successfully")


if __name__ == "__main__":
    unittest.main()
