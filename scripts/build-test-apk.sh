#!/usr/bin/env bash
# Build the isolated test app with an existing Android SDK, without Gradle downloads.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ANDROID_HOME:?Set ANDROID_HOME to an installed SDK}"
platform="${PHONE_USE_TEST_PLATFORM:-android-35}"
build_tools="${PHONE_USE_TEST_BUILD_TOOLS:-35.0.0}"
tools="$ANDROID_HOME/build-tools/$build_tools"
android_jar="$ANDROID_HOME/platforms/$platform/android.jar"
out="$PWD/artifacts/android"
mkdir -p "$out/classes" "$out/dex"
javac -source 8 -target 8 -bootclasspath "$android_jar" -d "$out/classes" tests/android/MainActivity.java
"$tools/d8" --lib "$android_jar" --min-api 26 --output "$out/dex" "$out/classes/org/phoneuse/fixture/"*.class
"$tools/aapt2" link -I "$android_jar" --manifest tests/android/AndroidManifest.xml -o "$out/unsigned.apk"
(cd "$out/dex" && zip -q -u "$out/unsigned.apk" classes.dex)
"$tools/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
if ! test -f "$out/test-only.keystore"; then
  keytool -genkeypair -keystore "$out/test-only.keystore" -storepass android -keypass android \
    -alias test -dname 'CN=phone-use test' -keyalg RSA -validity 3650 -noprompt
fi
"$tools/apksigner" sign --ks "$out/test-only.keystore" --ks-pass pass:android \
  --out "$out/phone-use-test.apk" "$out/aligned.apk"
"$tools/apksigner" verify "$out/phone-use-test.apk"
printf '%s\n' "$out/phone-use-test.apk"
