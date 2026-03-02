#!/bin/bash
# =============================================================================
# Cloudflare クイックトンネル起動スクリプト
# llama-server とは独立して起動・停止できる。
# 使い方: ./scripts/tunnel.sh [ポート番号]
#   例: ./scripts/tunnel.sh       # デフォルト 8080
#       ./scripts/tunnel.sh 8081
# =============================================================================

set -euo pipefail

PORT="${1:-${PORT:-8080}}"
TUNNEL_PROTOCOL="${TUNNEL_PROTOCOL:-http2}"

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "エラー: ポート番号が不正です: $PORT"
    echo "1 から 65535 の数値を指定してください。"
    exit 1
fi

if ! command -v cloudflared &>/dev/null; then
    echo "エラー: cloudflared が見つかりません。インストールしてください。"
    echo ""
    echo "  Ubuntu/Debian:"
    echo "    curl -L -o cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    echo "    sudo dpkg -i cloudflared.deb"
    exit 1
fi

if command -v curl &>/dev/null; then
    if ! curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
        echo "警告: http://127.0.0.1:${PORT}/ に接続できません。"
        echo "       cloudflared は起動できますが、転送先の llama-server が未起動だと外部からは失敗します。"
        echo ""
    fi
fi

echo "Cloudflare トンネル起動中: http://localhost:${PORT}"
echo "接続プロトコル: ${TUNNEL_PROTOCOL}"
echo "公開 URL は起動後のログに表示されます（https://xxxx.trycloudflare.com）"
echo "停止: Ctrl+C"
echo ""

exec cloudflared tunnel --protocol "${TUNNEL_PROTOCOL}" --url "http://localhost:${PORT}"
