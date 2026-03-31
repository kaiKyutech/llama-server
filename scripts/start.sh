#!/bin/bash
# =============================================================================
# llama-server 起動スクリプト
# 使い方: ./scripts/start.sh configs/gpu_only.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LLAMA_BIN="$PROJECT_DIR/llama.cpp/build/bin/llama-server"

resolve_cli_path() {
    local input_path="$1"

    if [[ "$input_path" = /* ]]; then
        printf '%s\n' "$input_path"
        return
    fi

    if [[ -f "$input_path" ]]; then
        (
            cd "$(dirname "$input_path")"
            printf '%s/%s\n' "$(pwd)" "$(basename "$input_path")"
        )
        return
    fi

    printf '%s/%s\n' "$PROJECT_DIR" "$input_path"
}

resolve_project_path() {
    local input_path="$1"

    if [[ -z "$input_path" ]]; then
        return
    fi

    if [[ "$input_path" = /* ]]; then
        printf '%s\n' "$input_path"
        return
    fi

    if [[ -n "${CONFIG_DIR:-}" && -f "$CONFIG_DIR/$input_path" ]]; then
        printf '%s/%s\n' "$CONFIG_DIR" "$input_path"
        return
    fi

    if [[ -f "$PROJECT_DIR/$input_path" ]]; then
        printf '%s/%s\n' "$PROJECT_DIR" "$input_path"
        return
    fi

    printf '%s/%s\n' "$PROJECT_DIR" "$input_path"
}

# 設定ファイルの確認
if [ -z "$1" ]; then
    echo "使い方: $0 <設定ファイル>"
    echo ""
    echo "  例: $0 configs/gpu_only.sh"
    echo "      $0 configs/cpu_only.sh"
    echo "      $0 configs/cpu_gpu.sh"
    exit 1
fi

CONFIG_FILE="$(resolve_cli_path "$1")"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "エラー: 設定ファイルが見つかりません: $CONFIG_FILE"
    exit 1
fi
CONFIG_DIR="$(dirname "$CONFIG_FILE")"

# 設定を読み込む
source "$CONFIG_FILE"

# llama-server の存在確認
if [ ! -f "$LLAMA_BIN" ]; then
    echo "エラー: llama-server が見つかりません。先に setup/install_llama.sh を実行してください。"
    exit 1
fi

MODEL_PATH="${MODEL_PATH:-}"
if [ -z "$MODEL_PATH" ]; then
    echo "エラー: MODEL_PATH は必須です: $CONFIG_FILE"
    exit 1
fi

MODEL_PATH="$(resolve_project_path "$MODEL_PATH")"
if [ ! -f "$MODEL_PATH" ]; then
    echo "エラー: モデルファイルが見つかりません: $MODEL_PATH"
    exit 1
fi

MMPROJ_PATH="${MMPROJ_PATH:-}"
if [ -n "$MMPROJ_PATH" ]; then
    MMPROJ_PATH="$(resolve_project_path "$MMPROJ_PATH")"
    if [ ! -f "$MMPROJ_PATH" ]; then
        echo "エラー: mmproj ファイルが見つかりません: $MMPROJ_PATH"
        exit 1
    fi
fi

# コマンド組み立て
CMD=("$LLAMA_BIN")
CMD+=(--model "$MODEL_PATH")

[ -n "$MMPROJ_PATH" ]           && CMD+=(--mmproj "$MMPROJ_PATH")
[ -n "${ALIAS:-}" ]             && CMD+=(--alias "$ALIAS")
[ -n "${N_GPU_LAYERS:-}" ]      && CMD+=(--n-gpu-layers "$N_GPU_LAYERS")
[ -n "${CTX_SIZE:-}" ]          && CMD+=(--ctx-size "$CTX_SIZE")
[ -n "${BATCH_SIZE:-}" ]        && CMD+=(--batch-size "$BATCH_SIZE")
[ -n "${UBATCH_SIZE:-}" ]       && CMD+=(--ubatch-size "$UBATCH_SIZE")
[ -n "${FLASH_ATTN:-}" ]        && CMD+=(--flash-attn "$FLASH_ATTN")
[ -n "${CACHE_TYPE_K:-}" ]      && CMD+=(--cache-type-k "$CACHE_TYPE_K")
[ -n "${CACHE_TYPE_V:-}" ]      && CMD+=(--cache-type-v "$CACHE_TYPE_V")
[ -n "${THREADS:-}" ]           && CMD+=(--threads "$THREADS")
[ -n "${THREADS_BATCH:-}" ]     && CMD+=(--threads-batch "$THREADS_BATCH")
[ -n "${CPU_MASK:-}" ]          && CMD+=(--cpu-mask "$CPU_MASK")
[ -n "${PARALLEL:-}" ]          && CMD+=(--parallel "$PARALLEL")
[ "${CONT_BATCHING:-}" = "false" ] && CMD+=(--no-cont-batching)
[ "${KV_UNIFIED:-}" = "false" ] && CMD+=(--no-kv-unified)
[ "${MLOCK:-}" = "true" ]       && CMD+=(--mlock)
[ -n "${NUMA:-}" ]              && CMD+=(--numa "$NUMA")
[ -n "${PRIO:-}" ]              && CMD+=(--prio "$PRIO")
[ -n "${HOST:-}" ]              && CMD+=(--host "$HOST")
[ -n "${PORT:-}" ]              && CMD+=(--port "$PORT")
[ -n "${API_KEY:-}" ]           && CMD+=(--api-key "$API_KEY")
[ -n "${TIMEOUT:-}" ]           && CMD+=(--timeout "$TIMEOUT")
[ -n "${THREADS_HTTP:-}" ]      && CMD+=(--threads-http "$THREADS_HTTP")
[ "${JINJA:-}" = "true" ]              && CMD+=(--jinja)
[ -n "${REASONING_FORMAT:-}" ]        && CMD+=(--reasoning-format "$REASONING_FORMAT")
[ -n "${REASONING_BUDGET:-}" ]        && CMD+=(--reasoning-budget "$REASONING_BUDGET")
[ -n "${CHAT_TEMPLATE_KWARGS:-}" ]    && CMD+=(--chat-template-kwargs "$CHAT_TEMPLATE_KWARGS")
[ -n "${LOG_VERBOSITY:-}" ]     && CMD+=(--verbosity "$LOG_VERBOSITY")

echo "設定ファイル: $CONFIG_FILE"
echo "起動コマンド: ${CMD[*]}"
echo ""

exec "${CMD[@]}"
