#!/usr/bin/env sh
set -eu

# Download large model assets intentionally excluded from Git. Existing files
# with the expected SHA-256 are skipped, so rerunning after interruption is safe.
WILOR_URL="https://www.dropbox.com/scl/fi/p7vxvq3prz4r46dzqoqer/pretrained_models.zip?rlkey=zwc2qnlgexrmxp7zd34cd5jio&st=c4pin9f0&dl=1"
HAND_URL="https://www.dropbox.com/scl/fi/ft9pcyce80hyxeuni9u7c/best_hand_model.pt?rlkey=hdghmzs69snszakdahb77cf84&st=7oealk32&dl=1"
METRABS_URL="https://www.dropbox.com/scl/fi/nzd62nooitrh68suvau2e/metrabs_eff2l_384px_800k_28ds_pytorch.zip?rlkey=cjycmqo5c6j188jb7en1esu5i&st=dvblobch&dl=1"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MODEL_DIR="$SCRIPT_DIR/../app/analysis/models"
WILOR_DIR="$MODEL_DIR/wilor_mini/pretrained_models"
HAND_DIR="$MODEL_DIR/hand_detector"
METRABS_DIR="$MODEL_DIR/metrabs_eff2l_384px_800k_28ds_pytorch"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/visionmd-models.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT HUP INT TERM

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "Neither sha256sum nor shasum is available." >&2
    exit 1
  fi
}

valid_file() {
  [ -f "$1" ] && [ "$(sha256 "$1")" = "$2" ]
}

require_tool() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required tool '$1' was not found." >&2
    exit 1
  }
}

download() {
  echo "Downloading $(basename "$2")..."
  curl --fail --location --retry 3 --output "$2" "$1"
}

install_from_archive() {
  source_file=$(find "$1" -type f -name "$2" -print | head -n 1)
  [ -n "$source_file" ] || { echo "Downloaded archive is missing $2." >&2; exit 1; }
  actual_hash=$(sha256 "$source_file")
  [ "$actual_hash" = "$3" ] || { echo "SHA-256 mismatch for $2 (got $actual_hash)." >&2; exit 1; }
  mkdir -p "$(dirname "$4")"
  cp "$source_file" "$4"
}

require_tool curl
require_tool unzip
[ -d "$MODEL_DIR" ] || { echo "Model directory $MODEL_DIR does not exist." >&2; exit 1; }

WILOR_OK=true
valid_file "$WILOR_DIR/wilor_final.ckpt" "3e97aafc7dd08d883a4cc5a027df61fdb6fda6136dbd1319405413862ada6bb2" || WILOR_OK=false
valid_file "$WILOR_DIR/detector.pt" "5ef3df44e42d2db52d4ffe91f83a22ce9925e2acc9abebf453f2c5d22e380033" || WILOR_OK=false
valid_file "$WILOR_DIR/MANO_RIGHT.pkl" "45d60aa3b27ef9107a7afd4e00808f307fd91111e1cfa35afd5c4a62de264767" || WILOR_OK=false
valid_file "$WILOR_DIR/mano_mean_params.npz" "efc0ec58e4a5cef78f3abfb4e8f91623b8950be9eff8b8e0dbb0d036ebc63988" || WILOR_OK=false
if [ "$WILOR_OK" = true ]; then
  echo "WiLoR models already exist and passed verification."
else
  download "$WILOR_URL" "$WORK_DIR/pretrained_models.zip"
  mkdir -p "$WORK_DIR/wilor"
  unzip -q "$WORK_DIR/pretrained_models.zip" -d "$WORK_DIR/wilor"
  install_from_archive "$WORK_DIR/wilor" wilor_final.ckpt "3e97aafc7dd08d883a4cc5a027df61fdb6fda6136dbd1319405413862ada6bb2" "$WILOR_DIR/wilor_final.ckpt"
  install_from_archive "$WORK_DIR/wilor" detector.pt "5ef3df44e42d2db52d4ffe91f83a22ce9925e2acc9abebf453f2c5d22e380033" "$WILOR_DIR/detector.pt"
  install_from_archive "$WORK_DIR/wilor" MANO_RIGHT.pkl "45d60aa3b27ef9107a7afd4e00808f307fd91111e1cfa35afd5c4a62de264767" "$WILOR_DIR/MANO_RIGHT.pkl"
  install_from_archive "$WORK_DIR/wilor" mano_mean_params.npz "efc0ec58e4a5cef78f3abfb4e8f91623b8950be9eff8b8e0dbb0d036ebc63988" "$WILOR_DIR/mano_mean_params.npz"
  echo "WiLoR models installed in $WILOR_DIR"
fi

if valid_file "$HAND_DIR/best_hand_model.pt" "12ec0eb2ec19324b85728c14a9de7dc4c2b0c93249ff79daff19fc9a2b58cb21"; then
  echo "Hand detector already exists and passed verification."
else
  download "$HAND_URL" "$WORK_DIR/best_hand_model.pt"
  valid_file "$WORK_DIR/best_hand_model.pt" "12ec0eb2ec19324b85728c14a9de7dc4c2b0c93249ff79daff19fc9a2b58cb21" || { echo "SHA-256 mismatch for best_hand_model.pt." >&2; exit 1; }
  mkdir -p "$HAND_DIR"
  cp "$WORK_DIR/best_hand_model.pt" "$HAND_DIR/best_hand_model.pt"
  echo "Hand detector installed in $HAND_DIR"
fi

METRABS_OK=true
valid_file "$METRABS_DIR/ckpt.pt" "cd9be4587f364d1c19bcdecfa2a5db1baa457ae1f100fe3aca29aef23437c1c3" || METRABS_OK=false
valid_file "$METRABS_DIR/config.yaml" "2ae9620540d6487c071d88bed723cae28e68e040fe38ee0e819c6be695af0d95" || METRABS_OK=false
valid_file "$METRABS_DIR/joint_info.npz" "de211b8679238955ada9a0f0b06bfccc2ea8fc5914d6feb9b3fd2d0b2b1cd97b" || METRABS_OK=false
valid_file "$METRABS_DIR/joint_transform_matrix.npy" "a1dd2b3c4807c1abd447300f142fe97673c40b510fac7d2cd2d6aa132a6a27cc" || METRABS_OK=false
valid_file "$METRABS_DIR/skeleton_infos.pkl" "952849909e6ad179ea297365e91534a2d06f0884e0a34cb7b5998ff1522a96c5" || METRABS_OK=false
if [ "$METRABS_OK" = true ]; then
  echo "MeTRAbs model already exists and passed verification."
else
  download "$METRABS_URL" "$WORK_DIR/metrabs.zip"
  mkdir -p "$WORK_DIR/metrabs"
  unzip -q "$WORK_DIR/metrabs.zip" -d "$WORK_DIR/metrabs"
  install_from_archive "$WORK_DIR/metrabs" ckpt.pt "cd9be4587f364d1c19bcdecfa2a5db1baa457ae1f100fe3aca29aef23437c1c3" "$METRABS_DIR/ckpt.pt"
  install_from_archive "$WORK_DIR/metrabs" config.yaml "2ae9620540d6487c071d88bed723cae28e68e040fe38ee0e819c6be695af0d95" "$METRABS_DIR/config.yaml"
  install_from_archive "$WORK_DIR/metrabs" joint_info.npz "de211b8679238955ada9a0f0b06bfccc2ea8fc5914d6feb9b3fd2d0b2b1cd97b" "$METRABS_DIR/joint_info.npz"
  install_from_archive "$WORK_DIR/metrabs" joint_transform_matrix.npy "a1dd2b3c4807c1abd447300f142fe97673c40b510fac7d2cd2d6aa132a6a27cc" "$METRABS_DIR/joint_transform_matrix.npy"
  install_from_archive "$WORK_DIR/metrabs" skeleton_infos.pkl "952849909e6ad179ea297365e91534a2d06f0884e0a34cb7b5998ff1522a96c5" "$METRABS_DIR/skeleton_infos.pkl"
  echo "MeTRAbs model installed in $METRABS_DIR"
fi

echo "All VisionMD model assets are installed and verified."

# YOLO pose for automatic subject suggestions.
if ! valid_file "$MODEL_DIR/yolo11n-pose.pt" "869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0"; then
  download "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.pt" "$WORK_DIR/yolo11n-pose.pt"
  valid_file "$WORK_DIR/yolo11n-pose.pt" "869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0" || { echo "YOLO pose SHA-256 mismatch." >&2; exit 1; }
  cp "$WORK_DIR/yolo11n-pose.pt" "$MODEL_DIR/yolo11n-pose.pt"
fi
