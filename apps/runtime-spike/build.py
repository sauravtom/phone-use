"""Small dependency-free Android build; run on AWS with its existing SDK/NDK/JDK."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--abi", choices=["arm64-v8a", "x86_64"], required=True)
    parser.add_argument("--target", choices=[28, 36], type=int, required=True)
    parser.add_argument("--native-extra", type=Path)
    parser.add_argument("--staged-runtime", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve() / f"{args.abi}-target{args.target}"
    out.mkdir(parents=True, exist_ok=True)
    sdk = args.sdk.resolve()
    bt = sdk / "build-tools/36.0.0"
    android = sdk / "platforms/android-36/android.jar"
    clang = sdk / "ndk/29.0.14206865/toolchains/llvm/prebuilt/linux-x86_64/bin"
    triple = "aarch64" if args.abi == "arm64-v8a" else "x86_64"
    compiler = clang / f"{triple}-linux-android26-clang"
    native = out / "native"
    native.mkdir(exist_ok=True)
    run(
        compiler,
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-fPIE",
        "-pie",
        "-Wl,-z,max-page-size=16384",
        HERE / "native/runner.c",
        "-o",
        native / "libspike_runner.so",
    )
    if args.native_extra:
        for item in args.native_extra.glob("*.so"):
            if args.staged_runtime and item.name == "libcodex.so":
                continue
            shutil.copyfile(item, native / item.name)
    package = f"dev.phoneuse.spike.{'legacy' if args.target == 28 else 'modern'}"
    manifest = out / "AndroidManifest.xml"
    manifest.write_text(f'''<manifest xmlns:android="http://schemas.android.com/apk/res/android"
        package="{package}" android:versionCode="1" android:versionName="0.1">
      <uses-sdk android:minSdkVersion="26" android:targetSdkVersion="{args.target}"/>
      <uses-permission android:name="android.permission.INTERNET"/>
      <application android:label="Runtime spike {args.target}" android:debuggable="true"
        android:allowBackup="false" android:extractNativeLibs="true"
        android:usesCleartextTraffic="false"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity android:name="dev.phoneuse.spike.MainActivity" android:exported="true"
          android:configChanges="orientation|screenSize">
          <intent-filter><action android:name="android.intent.action.MAIN"/>
            <category android:name="android.intent.category.LAUNCHER"/></intent-filter>
        </activity>
      </application>
    </manifest>''')
    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    for name in (
        ("runtime-manifest.json",)
        if args.staged_runtime
        else ("runtime.zip", "runtime-manifest.json")
    ):
        shutil.copyfile(args.runtime / name, assets / name)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    (assets / "build.json").write_text(
        json.dumps(
            {
                "sourceCommit": commit,
                "abi": args.abi,
                "targetSdk": args.target,
                "runtimeDelivery": "staged" if args.staged_runtime else "bundled",
                "fixture": "Ubuntu noble packages; see packages.txt in runtime artifacts",
                "warning": "Debug research APK, not a release app or security sandbox",
            }
        )
    )
    unsigned = out / "unsigned.apk"
    run(
        bt / "aapt2",
        "link",
        "-o",
        unsigned,
        "--manifest",
        manifest,
        "-I",
        android,
        "-A",
        assets,
        "-0",
        "zip",
    )
    classes = out / "classes"
    classes.mkdir(exist_ok=True)
    run(
        "javac",
        "--release",
        "8",
        "-classpath",
        android,
        "-d",
        classes,
        *HERE.glob("src/**/*.java"),
    )
    dex = out / "dex"
    dex.mkdir(exist_ok=True)
    run(bt / "d8", "--lib", android, "--min-api", "26", "--output", dex, *classes.rglob("*.class"))
    with ZipFile(unsigned, "a", ZIP_DEFLATED) as apk:
        apk.write(dex / "classes.dex", "classes.dex")
        for so in native.glob("*.so"):
            apk.write(so, f"lib/{args.abi}/{so.name}")
    aligned = out / "aligned.apk"
    run(bt / "zipalign", "-f", "-p", "4", unsigned, aligned)
    key = args.out.resolve() / "research-debug.jks"
    if not key.exists():
        run(
            "keytool",
            "-genkeypair",
            "-keystore",
            key,
            "-storepass",
            "android",
            "-keypass",
            "android",
            "-alias",
            "research",
            "-dname",
            "CN=Runtime Spike Debug",
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "365",
        )
        key.chmod(0o600)
    apk = args.out.resolve() / f"runtime-spike-{args.abi}-target{args.target}.apk"
    run(
        bt / "apksigner",
        "sign",
        "--ks",
        key,
        "--ks-pass",
        "pass:android",
        "--key-pass",
        "pass:android",
        "--out",
        apk,
        aligned,
    )
    run(bt / "apksigner", "verify", apk)
    print(
        json.dumps(
            {
                "apk": str(apk),
                "sourceCommit": commit,
                "sha256": hashlib.file_digest(apk.open("rb"), "sha256").hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
