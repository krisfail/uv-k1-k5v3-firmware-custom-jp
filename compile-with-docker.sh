#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------
# Usage:
#   ./compile-with-docker.sh [Preset] [CMake options...]
# Example:
#   ./compile-with-docker.sh JpRxOnly -DCMAKE_BUILD_TYPE=Debug
#   ./compile-with-docker.sh JpRxOnlyFontTest
# Default preset: "JpRxOnly".
# ---------------------------------------------

IMAGE=uvk1-uvk5v3
PRESET=JpRxOnly
case "${1:-}" in
  JpRxOnly|JpRxOnlyFontTest)
    PRESET="$1"
    shift
    ;;
esac
EXTRA_ARGS=("$@")

# ---------------------------------------------
# Build the Docker image (only needed once)
# ---------------------------------------------
if [[ -z "$(docker images -q "$IMAGE")" ]]; then
  echo "Building Docker image..."
  docker build -t "$IMAGE" .
fi

# ---------------------------------------------
# Clean existing CMake cache to ensure toolchain reload
# ---------------------------------------------
rm -rf build
export MSYS_NO_PATHCONV=1
# ---------------------------------------------
# Function to build one supported preset
# ---------------------------------------------
build_preset() {
  local preset="$1"
  echo ""
  echo "=== 🚀 Building preset: ${preset} ==="
  echo "---------------------------------------------"
  docker run --rm \
    -u "$(id -u):$(id -g)" \
    -v "$PWD":/src -w /src "$IMAGE" \
    bash -c 'set -euo pipefail
             which arm-none-eabi-gcc
             arm-none-eabi-gcc --version
             cmake --preset "$1" "${@:2}"
             cmake --build --preset "$1" -j2' \
    bash "$preset" "${EXTRA_ARGS[@]}"
  echo "✅ Done: ${preset}"
}

build_preset "$PRESET"
