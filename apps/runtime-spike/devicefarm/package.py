"""Create the small Device Farm test bundle on AWS, pinning the existing APKs."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--targets", type=int, nargs="+", choices=(28, 36), default=(28, 36))
    args = parser.parse_args()
    records = {}
    for target in args.targets:
        apk = args.apks / f"runtime-spike-arm64-v8a-target{target}.apk"
        with apk.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        with ZipFile(apk) as archive:
            build = json.loads(archive.read("assets/build.json"))
            manifest = hashlib.sha256(archive.read("assets/runtime-manifest.json")).hexdigest()
        if build["abi"] != "arm64-v8a" or build["targetSdk"] != target:
            raise ValueError("APK ABI/target mismatch")
        if build.get("runtimeDelivery", "bundled") != "bundled":
            raise ValueError("Bundled APKs required")
        records[str(target)] = {
            "apkSha256": digest,
            "build": build,
            "runtimeManifestSha256": manifest,
        }
    here = Path(__file__).parent
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.out, "w", ZIP_DEFLATED) as archive:
        for name in ("tests/test_runtime.py", "requirements.txt"):
            archive.write(here / name, name)
        archive.writestr("tests/expected.json", json.dumps(records, indent=2) + "\n")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
