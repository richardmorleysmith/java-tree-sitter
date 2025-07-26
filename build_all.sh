#!/usr/bin/env bash

set -e  # Exit on error

if [ -z "$1" ]; then
  echo "Error: Output directory not provided."
  echo "Usage: $0 <output_directory>"
  exit 1
fi

output_directory="$1"

macos_targets=(
  "Darwin arm64"
  "Darwin x86_64"
)

linux_targets=(
  "Linux arm64"
  "Linux x86_64"
)

export DOCKER_BUILDKIT=1  # Enable BuildKit

for target in "${linux_targets[@]}"; do
  read -r system arch <<< "$target"
  echo "Building for $system - $arch"
  docker build --no-cache --platform=linux/"$arch" --output "${output_directory}" --build-arg ARCH="$arch" -f Dockerfile .
done

for target in "${macos_targets[@]}"; do
  read -r system arch <<< "$target"
  echo "Building for $system - $arch to $output_directory"
  python build.py -o "$output_directory" -s "$system" -a "$arch"
done

echo "All builds done."
