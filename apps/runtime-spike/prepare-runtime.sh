#!/usr/bin/env bash
# Run only on the existing Linux build host. Outputs never belong in Git.
set -euo pipefail
out=${1:?Usage: prepare-runtime.sh ABSOLUTE_OUTPUT_DIRECTORY}
[[ "$out" = /* ]] || exit 2
mkdir -p "$out"
docker pull ubuntu:24.04
docker image inspect ubuntu:24.04 --format '{{json .RepoDigests}}' > "$out/builder-image.json"
for arch in amd64 arm64; do
  mkdir -p "$out/$arch"
  docker run --rm -e RUNTIME_ARCH="$arch" -v "$out/$arch:/out" ubuntu:24.04 bash -euc '
    export DEBIAN_FRONTEND=noninteractive
    arch=$RUNTIME_ARCH
    mirror=http://archive.ubuntu.com/ubuntu
    [[ "$arch" = arm64 ]] && mirror=http://ports.ubuntu.com/ubuntu-ports
    printf "deb [arch=%s] %s noble main universe\n" "$arch" "$mirror" > /tmp/sources.list
    : > /tmp/empty-status
    mkdir -p /out/debs/partial /out/root
    opts=(-o "APT::Architecture=$arch" -o Dir::Etc::sourcelist=/tmp/sources.list
      -o Dir::Etc::sourceparts=- -o Dir::State::status=/tmp/empty-status
      -o Dir::Cache::archives=/out/debs -o APT::Sandbox::User=root)
    apt-get "${opts[@]}" update
    apt-get "${opts[@]}" --download-only --yes --no-install-recommends install \
      bash python3 git curl ca-certificates coreutils libc-bin
    for pkg in /out/debs/*.deb; do
      dpkg-deb -x "$pkg" /out/root
      dpkg-deb -f "$pkg" Package Version Architecture
      sha256sum "$pkg"
    done > /out/packages.txt
    mkdir -p /out/root/etc/ssl/certs /out/root/tmp /out/root/dev /out/root/proc
    cat /out/root/usr/share/ca-certificates/mozilla/*.crt > /out/root/etc/ssl/certs/ca-certificates.crt
    # Package extraction does not run the shell-alternative maintainer scripts.
    # Git helpers and shebangs require /bin/sh; /bin is the packaged usr/bin link.
    if [[ ! -e /out/root/usr/bin/sh && ! -L /out/root/usr/bin/sh ]]; then
      ln -s bash /out/root/usr/bin/sh
    fi
    # No maintainer scripts or foreign-architecture binaries are executed.
    chown -R '"$(id -u):$(id -g)"' /out
  '
done
