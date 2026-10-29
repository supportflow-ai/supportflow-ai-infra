"""MinIO thật: bucket tồn tại, init lặp và dependency bị chặn khi sai mật khẩu."""

import json
import os
from pathlib import Path
import subprocess
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]


class LiveMinioTests(unittest.TestCase):
    def test_real_initialization_replay_and_failure_gate(self):
        project = "sf-minio-test-" + uuid.uuid4().hex
        command = ["docker", "compose", "-p", project, "-f", "tests/integration/compose.minio.yml"]
        password = uuid.uuid4().hex
        env = dict(os.environ, TEST_MINIO_USER="ci_custom_user", TEST_MINIO_PASSWORD=password,
                   TEST_MINIO_INIT_PASSWORD=password, TEST_MINIO_BUCKET="ci-custom-bucket")

        def run(*args, check=True):
            result = subprocess.run([*command, *args], cwd=ROOT, env=env, capture_output=True,
                                    text=True, encoding="utf-8", timeout=180)
            if check:
                self.assertEqual(result.returncode, 0, result.stderr)
            return result

        # Mọi lệnh, kể cả cleanup, đều giới hạn ở project UUID tạo trong test này.
        try:
            run("up", "-d", "minio")
            for _ in range(2):
                run("run", "--rm", "minio-init")
            run("run", "--rm", "--no-deps", "--entrypoint", "/bin/sh", "minio-init", "-ec",
                'mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; '
                'mc stat "local/$MINIO_DEFAULT_BUCKET" >/dev/null')
            env["TEST_MINIO_INIT_PASSWORD"] = "intentionally_wrong_password"
            failed = run("up", "-d", "protected-service", check=False)
            self.assertNotEqual(failed.returncode, 0, "Init lỗi phải chặn service phụ thuộc")
            container_ids = run("ps", "-a", "-q", "protected-service").stdout.split()
            for container_id in container_ids:
                state = subprocess.run(["docker", "inspect", "--format", "{{json .State}}", container_id],
                                       capture_output=True, text=True, check=True, timeout=20)
                self.assertEqual(json.loads(state.stdout)["Status"], "created")
        finally:
            run("down", "--remove-orphans")


if __name__ == "__main__":
    unittest.main()
