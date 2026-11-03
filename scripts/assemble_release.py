"""Ghép bằng chứng GHCR của năm image; không build, push hoặc triển khai."""

import argparse
import hashlib
import json
from pathlib import Path
import re

IMAGES = {
    "servicedesk-api": ("API_IMAGE", "ai-it-service-desk"),
    "servicedesk-worker": ("WORKER_IMAGE", "ai-it-service-desk"),
    "servicedesk-database": ("DATABASE_IMAGE", "ai-it-service-desk"),
    "servicedesk-web": ("WEB_IMAGE", "ai-it-service-desk-web"),
    "ai-service": ("AI_IMAGE", "ai-service"),
}


def assemble(artifacts, release_id, migration, contract_bytes):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}", release_id):
        raise ValueError("Release ID không hợp lệ.")
    if not re.fullmatch(r"[0-9]{14}_[A-Za-z0-9_]+", migration):
        raise ValueError("Cần ID migration đầy đủ thuộc image Database đã chọn.")
    images, sources = {}, {}
    for artifact in artifacts:
        commit = artifact.get("commit", "")
        if not re.fullmatch(r"[a-f0-9]{40}", commit):
            raise ValueError("Bằng chứng thiếu SHA nguồn đầy đủ.")
        for image, reference in artifact.get("images", {}).items():
            if image not in IMAGES or image in images:
                raise ValueError("Image không thuộc sản phẩm hoặc bị lặp.")
            _, repo = IMAGES[image]
            if artifact.get("repository") != "supportflow-ai/" + repo:
                raise ValueError("Repository nguồn không đúng chủ sở hữu image.")
            if repo in sources and sources[repo] != commit:
                raise ValueError("API/Worker/Database phải được build từ cùng SHA backend.")
            if not isinstance(reference, str) or not re.fullmatch(
                    "ghcr.io/supportflow-ai/" + re.escape(image) + r"@sha256:[a-f0-9]{64}", reference):
                raise ValueError("Chỉ nhận image GHCR theo digest bất biến.")
            sources[repo] = commit
            images[image] = reference
    if set(images) != set(IMAGES):
        raise ValueError("Cần đủ năm image API/Worker/Database/Web/AI.")
    return {"schemaVersion": 1, "releaseId": release_id, "sources": sources,
            "migration": migration, "aiContractVersion": "v1",
            "aiContractSha256": hashlib.sha256(contract_bytes).hexdigest(), "images": images}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", action="append", required=True, type=Path)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--migration", required=True)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = assemble([json.loads(path.read_text(encoding="utf-8")) for path in args.artifact],
                            args.release_id, args.migration, args.contract.read_bytes())
    except (ValueError, OSError, TypeError) as error:
        parser.exit(1, f"Không tạo release: {error}\n")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (args.output / "images.env").write_text("".join(
        f"{IMAGES[name][0]}={manifest['images'][name]}\n" for name in IMAGES), encoding="utf-8")
    print(f"Đã kiểm tra và tạo manifest {args.release_id}; chưa thực hiện triển khai.")


if __name__ == "__main__":
    main()
