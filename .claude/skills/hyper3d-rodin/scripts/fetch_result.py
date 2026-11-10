"""Download all files of a completed Rodin generation (signed URLs are temporary).

    python3 fetch_result.py <generation_id> --out DIR

Requires the `hyper3d` CLI, logged in. Never prints the signed URLs.
"""
import argparse
import json
import os
import subprocess
import urllib.request


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("generation_id")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = subprocess.run(["hyper3d", "--output", "json", "result", a.generation_id], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("hyper3d result failed: " + (r.stderr or r.stdout).strip().splitlines()[0]
                         + "\nIf it is INVALID_REQUEST, ask the user to download from the Hyper3D website.")
    data = json.loads(r.stdout)
    os.makedirs(a.out, exist_ok=True)
    for f in data.get("files", []):
        dest = os.path.join(a.out, os.path.basename(f["name"]))
        with urllib.request.urlopen(f["url"]) as resp, open(dest, "wb") as fh:
            fh.write(resp.read())
        print(f"{f['role']:8s} {os.path.getsize(dest):>10d}  {dest}")


if __name__ == "__main__":
    main()
