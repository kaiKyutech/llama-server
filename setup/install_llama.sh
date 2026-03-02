#!/bin/bash
# llama.cpp CUDA ビルドスクリプト
# Ubuntu 24.04 + CUDA 12.x 対応
# 対応GPU: RTX 30xx (sm_86), RTX 40xx (sm_89), A100 (sm_80)
#
# 使い方:
#   ./install_llama.sh              # 接続中のGPUを自動検出
#   CUDA_ARCH=86 ./install_llama.sh # RTX 30xx など手動指定
#   CUDA_ARCH=80 ./install_llama.sh # A100 など手動指定

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LLAMA_DIR="$PROJECT_DIR/llama.cpp"

# CUDA アーキテクチャの決定
# 環境変数 CUDA_ARCH が未設定の場合は "native"（接続中GPUを自動検出）
CUDA_ARCH="${CUDA_ARCH:-native}"
echo "CUDA_ARCH: $CUDA_ARCH"

echo "=== 依存パッケージのインストール ==="
if sudo -n true 2>/dev/null; then
    # sudo が使える環境（A100 等）: apt-get でインストール
    sudo apt-get update
    sudo apt-get install -y cmake build-essential libcurl4-openssl-dev libcublas-dev
    # システム CUDA があれば CUDA_PATH を自動設定（conda の nvcc と混在する環境向け）
    if [ -d /usr/local/cuda ] && [ -z "${CUDA_PATH:-}" ]; then
        CUDA_PATH=/usr/local/cuda
        echo "CUDA_PATH: ${CUDA_PATH}"
    fi
elif command -v conda &>/dev/null; then
    # sudo なし + conda 環境（JupyterHub 等）: conda でインストール
    echo "sudo が使えないため conda でインストールします..."
    conda install -y -c conda-forge cmake libcurl compilers
    conda install -y -c nvidia cuda-toolkit
    # CUDA_PATH が未設定の場合は conda prefix を自動設定
    CUDA_PATH="${CUDA_PATH:-${CONDA_PREFIX}}"
    echo "CUDA_PATH: ${CUDA_PATH}"
else
    echo "sudo も conda もないためインストールをスキップします（cmake/gcc が利用可能とみなします）"
fi

echo "=== llama.cpp のクローン ==="
if [ -d "$LLAMA_DIR" ]; then
    echo "既存の llama.cpp ディレクトリを更新します..."
    cd "$LLAMA_DIR"
    git pull
else
    git clone https://github.com/ggerganov/llama.cpp "$LLAMA_DIR"
    cd "$LLAMA_DIR"
fi

echo "=== CUDA 対応でビルド (ARCH=$CUDA_ARCH) ==="
cmake -B build \
    -DGGML_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" \
    -DCMAKE_BUILD_TYPE=Release \
    ${CUDA_PATH:+-DCUDAToolkit_ROOT="${CUDA_PATH}"} \
    ${CUDA_PATH:+-DCMAKE_CUDA_FLAGS="-I${CUDA_PATH}/include"}

cmake --build build --config Release -j$(nproc)

echo ""
echo "=== ビルド完了 ==="
echo "実行ファイル: $LLAMA_DIR/build/bin/llama-server"
echo ""
echo "動作確認:"
"$LLAMA_DIR/build/bin/llama-server" --version
