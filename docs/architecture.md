# アーキテクチャと設計方針

## なぜ llama.cpp か

- vLLM は VRAM に全モデルを載せる前提のため、大型モデルでは動作しない
- Ollama は手軽だが並列処理や細かいチューニングが難しい
- llama.cpp は CPU / GPU / 混合オフロードを柔軟に制御でき、環境依存が少ない

## なぜ Python を llama-server の前段に置くか

llama-server 単体でも `--parallel` オプションで並列スロットを持てるが、それは単一プロセス内の話。
複数の llama-server プロセスをまたいだロードバランスや動的な起動・停止は Python 層で管理する。

また、Python から `llama_cpp` ライブラリを直接インポートする方式（llama-cpp-python）は、
プロセス内に推論が閉じてしまうため並列化の柔軟性が失われる。そのため採用しない。

## なぜ Cloudflare Tunnel か

- 固定グローバル IP が不要
- ポート開放・ファイアウォール設定が不要
- 無料プランで HTTPS エンドポイントを公開できる

## 全体構成

```
[クライアント (curl / OpenAI SDK 等)]
        ↓ OpenAI 互換リクエスト (/v1/chat/completions 等)
[Python サーバー (FastAPI)]   ← ルーティング・認証・ロードバランス
        ↓
[llama-server × N プロセス]  ← llama.cpp ネイティブ、並列スロット対応
        ↓
[CUDA GPU / CPU / 混合オフロード]
```

## 対応環境

| 環境 | GPU | VRAM | CUDA Arch |
|------|-----|------|-----------|
| 開発（WSL2） | RTX 4070 Ti | 12GB | sm_89 |
| 本番A | RTX 3090 Ti | 24GB | sm_86 |
| 本番B | A100 40GB | 40GB | sm_80 |
| CPU only | なし | - | - |

## GPU / CPU モード切り替えの仕組み

llama-server の `--n-gpu-layers (-ngl)` でモデルの何層を GPU に載せるかを制御する。

| モード | 値 | 用途 |
|--------|---|------|
| GPU only | `99`（全層） | VRAM に収まる 8B 程度 |
| CPU + GPU | `20` など中間値 | 27B など VRAM に収まらないモデル |
| CPU only | `0` | GPU なし環境 |

ビルド時は `CUDA_ARCH` 環境変数で GPU アーキテクチャを指定。デフォルトは `native`（自動検出）。

## Git 運用方針

- スクリプト・設定・ソースコードは Git 管理
- `models/`（.gguf）・`llama.cpp/`（ビルド済みバイナリ）・`.env` は Git 管理外
- WSL2 上で開発し、GitHub 経由で別サーバーに展開する
