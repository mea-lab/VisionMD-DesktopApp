#!/usr/bin/env sh
set -eu

# The implementation is versioned in app/analysis/models/metrabs_pytorch.
# This script retrieves only the large, local checkpoint package needed by it.
MODEL_URL="https://www.dropbox.com/scl/fi/nzd62nooitrh68suvau2e/metrabs_eff2l_384px_800k_28ds_pytorch.zip?rlkey=cjycmqo5c6j188jb7en1esu5i&st=t1dtf5pn&dl=1"
MODEL_NAME="metrabs_eff2l_384px_800k_28ds_pytorch"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODEL_DIR="$SCRIPT_DIR/../app/analysis/models"
TARGET_DIR="$MODEL_DIR/$MODEL_NAME"
ZIP_FILE="$MODEL_DIR/$MODEL_NAME.zip"

if [ -f "$TARGET_DIR/ckpt.pt" ]; then
  echo "$TARGET_DIR/ckpt.pt already exists, skipping download"
  exit 0
fi

if [ ! -d "$MODEL_DIR" ]; then
  echo "Model directory $MODEL_DIR does not exist" >&2
  exit 1
fi

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
trap 'rm -f "$ZIP_FILE"' EXIT

echo "Downloading $MODEL_NAME from Dropbox..."
curl --fail --location --retry 3 --output "$ZIP_FILE" "$MODEL_URL"

echo "Extracting checkpoint package..."
unzip -q "$ZIP_FILE" -d "$TARGET_DIR"

if [ ! -f "$TARGET_DIR/ckpt.pt" ] || [ ! -f "$TARGET_DIR/config.yaml" ]; then
  echo "Downloaded archive is missing required MeTRAbs files." >&2
  rm -rf "$TARGET_DIR"
  exit 1
fi

echo "$MODEL_NAME downloaded and extracted to $TARGET_DIR"
