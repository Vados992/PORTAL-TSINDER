"""Hash distributable Git source paths, excluding this manifest itself."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root)
files = {}
for raw in paths.decode().split("\0"):
    if raw and raw != "release-manifest.json" and (root/raw).is_file():
        files[raw] = hashlib.sha256((root/raw).read_bytes()).hexdigest()
manifest = {"version": "0.1.0", "algorithm": "sha256", "files": dict(sorted(files.items()))}
(root/"release-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(f"Manifest covers {len(files)} source and validation files")
