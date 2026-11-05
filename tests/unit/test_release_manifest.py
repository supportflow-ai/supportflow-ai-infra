import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("assemble_release", ROOT / "scripts/assemble_release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseManifestTests(unittest.TestCase):
    def artifacts(self):
        # Synthetic fixtures, never published images.
        return [{"repository": "supportflow-ai/" + repo, "commit": "a" * 40,
                 "images": {name: "ghcr.io/supportflow-ai/" + name + "@sha256:" + "b" * 64}}
                for name, (_, repo) in release.IMAGES.items()]

    def assemble(self, artifacts):
        return release.assemble(artifacts, "synthetic-release", "20261102192104_AddAttachmentUploadIntents", b"contract")

    def test_accepts_complete_digest_set_and_records_source_contract(self):
        result = self.assemble(self.artifacts())
        self.assertEqual(len(result["images"]), 5)
        self.assertEqual(len(result["sources"]), 3)
        self.assertEqual(result["aiContractVersion"], "v1")
        self.assertEqual(len(result["aiContractSha256"]), 64)

    def test_rejects_tags_empty_digests_and_foreign_registries(self):
        for ref in ("ghcr.io/supportflow-ai/servicedesk-api:latest", "ghcr.io/supportflow-ai/servicedesk-api@",
                    "untrusted.invalid/servicedesk-api@sha256:" + "b" * 64):
            with self.subTest(ref=ref):
                artifacts = self.artifacts()
                artifacts[0]["images"]["servicedesk-api"] = ref
                with self.assertRaises(ValueError):
                    self.assemble(artifacts)

    def test_rejects_incomplete_or_duplicate_image_sets(self):
        for artifacts in (self.artifacts()[:-1], self.artifacts() + [self.artifacts()[0]]):
            with self.assertRaises(ValueError):
                self.assemble(artifacts)

    def test_rejects_mixed_backend_commits(self):
        artifacts = self.artifacts()
        artifacts[1]["commit"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "cùng SHA"):
            self.assemble(artifacts)

    def test_rejects_wrong_repository_and_short_commit(self):
        for key, value in (("repository", "other/ai-it-service-desk"), ("commit", "abcdef0")):
            artifacts = self.artifacts()
            artifacts[0][key] = value
            with self.assertRaises(ValueError):
                self.assemble(artifacts)


class ReleaseComposeTests(unittest.TestCase):
    def config(self, environment):
        env = dict(os.environ, DEPLOY_ENV=environment)
        for image, (variable, _) in release.IMAGES.items():
            env[variable] = "ghcr.io/supportflow-ai/" + image + "@sha256:" + "b" * 64
        result = subprocess.run(["docker", "compose", "--env-file", "deploy/example.env", "-f",
                                 "deploy/compose.release.yml", "config", "--format", "json"],
                                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_application_services_have_no_sibling_build_context(self):
        config = self.config("staging")
        for name in ("api-1", "api-2", "worker", "migration", "web", "ai-service"):
            with self.subTest(service=name):
                service = config["services"][name]
                self.assertNotIn("build", service)
                self.assertRegex(service["image"], r"@sha256:[a-f0-9]{64}$")

    def test_staging_and_production_have_distinct_volumes_and_networks(self):
        stage, production = self.config("staging"), self.config("production")
        for kind in ("volumes", "networks"):
            self.assertTrue({value["name"] for value in stage[kind].values()}.isdisjoint(
                {value["name"] for value in production[kind].values()}))

    def test_backend_uses_application_storage_credentials_and_real_ai_settings(self):
        services = self.config("staging")["services"]
        for name in ("api-1", "api-2", "worker"):
            self.assertEqual(services[name]["environment"]["Minio__AccessKey"],
                             services["minio-init"]["environment"]["MINIO_APP_ACCESS_KEY"])
            self.assertNotEqual(services[name]["environment"]["Minio__AccessKey"],
                                services["minio"]["environment"]["MINIO_ROOT_USER"])
        self.assertEqual(services["ai-service"]["environment"]["SUPPORTFLOW_AI_ENVIRONMENT"], "production")
        self.assertEqual(services["ai-service"]["environment"]["SUPPORTFLOW_AI_CLASSIFIER_PROVIDER"], "rule")

    def test_knowledge_pipeline_uses_pgvector_and_internal_cpu_embeddings(self):
        services = self.config("staging")["services"]
        self.assertRegex(services["postgres"]["image"], r"^pgvector/pgvector:0\.8\.1-pg16-bookworm@sha256:[a-f0-9]{64}$")
        ai = services["ai-service"]
        self.assertNotIn("ports", ai)
        self.assertEqual(ai["environment"]["SUPPORTFLOW_AI_EMBEDDING_PROVIDER"], "local-e5")
        for name in ("api-1", "api-2", "worker"):
            config = services[name]["environment"]
            self.assertEqual(config["KnowledgeIndex__Enabled"], "true")
            self.assertEqual(config["KnowledgeIndex__Endpoint"], "http://ai-service:8000")
            self.assertEqual(config["KnowledgeIndex__BearerToken"],
                             ai["environment"]["SUPPORTFLOW_AI_SERVICE_TOKEN"])


if __name__ == "__main__":
    unittest.main()
