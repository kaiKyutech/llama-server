# llama-server

llama.cpp の `llama-server` を推論バックエンドとして使うセルフホスト LLM サーバー。
OpenAI 互換 API を提供しつつ、GPU only / CPU only / CPU+GPU 混合に対応する。

設計の背景や詳細は [docs/architecture.md](docs/architecture.md) を、開発フェーズは [docs/phases.md](docs/phases.md) を参照。

---

## ディレクトリ構成

```
llama-server/
├── README.md
├── CLAUDE.md                   # Claude Code 向け作業指針
├── docs/
│   ├── architecture.md         # 設計方針・背景
│   └── phases.md               # フェーズ計画
├── setup/
│   └── install_llama.sh        # llama.cpp ビルドスクリプト
├── configs/
│   ├── gpu_only.sh             # GPU only モード設定
│   ├── cpu_only.sh             # CPU only モード設定
│   └── cpu_gpu.sh              # CPU+GPU 混合モード設定
├── scripts/
│   ├── start.sh                # llama-server 起動スクリプト
│   ├── tunnel.sh               # Cloudflare クイックトンネル起動
│   ├── chat.py                 # インタラクティブチャット
│   └── bench.py                # 並列ベンチマーク
└── models/                     # モデルファイル置き場（git 管理外）
```

---

## セットアップ

### 1. リポジトリをクローン

```bash
git clone git@github.com:kaiKyutech/llama-server.git
cd llama-server
```

### 2. uv をインストール

Python スクリプトの実行に使用する。インストール後はターミナルを再起動すること。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. llama.cpp をビルド

```bash
chmod +x setup/install_llama.sh

# GPU を自動検出してビルド（推奨）
./setup/install_llama.sh

# GPU アーキテクチャを手動指定する場合
CUDA_ARCH=89 ./setup/install_llama.sh   # RTX 40xx
CUDA_ARCH=86 ./setup/install_llama.sh   # RTX 30xx
CUDA_ARCH=80 ./setup/install_llama.sh   # A100
CUDA_ARCH=0  ./setup/install_llama.sh   # CPU only（CUDA 不要）
```

### llama.cpp のアップデート

新しいモデルに対応したいときは同じスクリプトを再実行するだけ。
既存ディレクトリがあれば差分更新・再ビルドのみ行うため初回より速く完了する。

```bash
./setup/install_llama.sh
```

### 4. モデルを配置

```bash
mkdir -p models
# models/ 以下にサブディレクトリを作り .gguf ファイルを置く（git 管理外）
# 例: models/Qwen3-VL-8B-Instruct-GGUF/
```

---

## 設定ファイルの編集（必須）

`configs/` 以下のファイルを使用環境に合わせて編集する。
**最低限 `MODEL_PATH` をモデルの実際のパスに合わせること。**

```
configs/
├── gpu_only.sh   # GPU only で動かす場合
├── cpu_only.sh   # CPU only で動かす場合
└── cpu_gpu.sh    # CPU+GPU 混合で動かす場合
```

各ファイル内のコメントアウトされたパラメータを外すことでチューニングできる。
パラメータの詳細は `docs/llama_help.md` を参照。

---

## 起動

```bash
chmod +x scripts/start.sh

./scripts/start.sh configs/gpu_only.sh    # GPU only
./scripts/start.sh configs/cpu_only.sh   # CPU only
./scripts/start.sh configs/cpu_gpu.sh    # CPU+GPU 混合
```

---

## 動作確認・実験

### curl で叩く

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-vl-8b","messages":[{"role":"user","content":"Hello"}]}'
```

### インタラクティブチャット（別ターミナルで）

末尾にトークン速度が表示される。

```bash
uv run scripts/chat.py

# オプション指定
uv run scripts/chat.py --url http://localhost:8080/v1 --model qwen3-vl-8b
```

### 並列ベンチマーク

複数セッションを同時投入してスループットを計測する。

```bash
uv run scripts/bench.py

# オプション指定
uv run scripts/bench.py --sessions 4 --prompt "やあ私は立夏。そちらも自己紹介お願い。"
```

---

## Cloudflare トンネル（外部公開）

llama-server とは独立して起動する。llama-server を再起動してもトンネルは維持される。

### cloudflared のインストール

```bash
curl -L -o cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

### トンネル起動（別ターミナルで）

```bash
chmod +x scripts/tunnel.sh
./scripts/tunnel.sh          # ポート 8080（デフォルト）
./scripts/tunnel.sh 8081     # ポートを変える場合
```

起動後のログに公開 URL が表示される：

```
https://xxxx.trycloudflare.com
```

この URL に OpenAI 互換 API としてアクセスできる。

---

## 別サーバーへの展開

```bash
# 初回
git clone git@github.com:kaiKyutech/llama-server.git
cd llama-server
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv インストール
./setup/install_llama.sh                           # llama.cpp ビルド
# models/ にモデルファイルを配置
# configs/ のパスを環境に合わせて編集

# 更新取り込み
git pull origin main
```
