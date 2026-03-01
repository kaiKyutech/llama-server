#!/bin/bash
# =============================================================================
# llama-server 起動スクリプト
# 使い方: ./scripts/start.sh configs/gpu_only.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LLAMA_BIN="$PROJECT_DIR/llama.cpp/build/bin/llama-server"

# 設定ファイルの確認
if [ -z "$1" ]; then
    echo "使い方: $0 <設定ファイル>"
    echo ""
    echo "  例: $0 configs/gpu_only.sh"
    echo "      $0 configs/cpu_only.sh"
    echo "      $0 configs/cpu_gpu.sh"
    exit 1
fi

CONFIG_FILE="$PROJECT_DIR/$1"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "エラー: 設定ファイルが見つかりません: $CONFIG_FILE"
    exit 1
fi

# 設定を読み込む
source "$CONFIG_FILE"

# llama-server の存在確認
if [ ! -f "$LLAMA_BIN" ]; then
    echo "エラー: llama-server が見つかりません。先に setup/install_llama.sh を実行してください。"
    exit 1
fi

# コマンド組み立て
CMD=("$LLAMA_BIN")
CMD+=(--model "$MODEL_PATH")

[ -n "$MMPROJ_PATH" ]        && CMD+=(--mmproj "$MMPROJ_PATH")
[ -n "$ALIAS" ]              && CMD+=(--alias "$ALIAS")
[ -n "$N_GPU_LAYERS" ]       && CMD+=(--n-gpu-layers "$N_GPU_LAYERS")
[ -n "$CTX_SIZE" ]           && CMD+=(--ctx-size "$CTX_SIZE")
[ -n "$BATCH_SIZE" ]         && CMD+=(--batch-size "$BATCH_SIZE")
[ -n "$UBATCH_SIZE" ]        && CMD+=(--ubatch-size "$UBATCH_SIZE")
[ -n "$FLASH_ATTN" ]         && CMD+=(--flash-attn "$FLASH_ATTN")
[ -n "$CACHE_TYPE_K" ]       && CMD+=(--cache-type-k "$CACHE_TYPE_K")
[ -n "$CACHE_TYPE_V" ]       && CMD+=(--cache-type-v "$CACHE_TYPE_V")
[ -n "$THREADS" ]            && CMD+=(--threads "$THREADS")
[ -n "$THREADS_BATCH" ]      && CMD+=(--threads-batch "$THREADS_BATCH")
[ -n "$PARALLEL" ]           && CMD+=(--parallel "$PARALLEL")
[ "$CONT_BATCHING" = "false" ] && CMD+=(--no-cont-batching)
[ "$KV_UNIFIED" = "false" ]  && CMD+=(--no-kv-unified)
[ "$MLOCK" = "true" ]        && CMD+=(--mlock)
[ -n "$NUMA" ]               && CMD+=(--numa "$NUMA")
[ -n "$PRIO" ]               && CMD+=(--prio "$PRIO")
[ -n "$HOST" ]               && CMD+=(--host "$HOST")
[ -n "$PORT" ]               && CMD+=(--port "$PORT")
[ -n "$API_KEY" ]            && CMD+=(--api-key "$API_KEY")
[ -n "$TIMEOUT" ]            && CMD+=(--timeout "$TIMEOUT")
[ -n "$THREADS_HTTP" ]       && CMD+=(--threads-http "$THREADS_HTTP")
[ -n "$REASONING_FORMAT" ]   && CMD+=(--reasoning-format "$REASONING_FORMAT")
[ -n "$REASONING_BUDGET" ]   && CMD+=(--reasoning-budget "$REASONING_BUDGET")
[ -n "$LOG_VERBOSITY" ]      && CMD+=(--verbosity "$LOG_VERBOSITY")

echo "設定ファイル: $1"
echo "起動コマンド: ${CMD[*]}"
echo ""

exec "${CMD[@]}"
