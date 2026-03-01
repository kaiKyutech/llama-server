# llama-server

llama.cpp の `llama-server` を推論バックエンドとして使い、Python でルーティング・管理を行うセルフホスト LLM サーバー。
OpenAI 互換 API を提供しつつ、GPU only / CPU only / CPU+GPU 混合に対応する。

設計の背景や詳細は [docs/architecture.md](docs/architecture.md) を、開発フェーズは [docs/phases.md](docs/phases.md) を参照。

---

## ディレクトリ構成

```
llama-server/
├── README.md
├── CLAUDE.md               # Claude Code 向け作業指針
├── docs/
│   ├── architecture.md     # 設計方針・背景
│   └── phases.md           # フェーズ計画
├── setup/
│   └── install_llama.sh    # llama.cpp ビルドスクリプト
├── configs/                # llama-server 起動オプション（今後追加）
├── server/                 # Python ルーティングサーバー（今後追加）
├── scripts/                # 起動・停止スクリプト（今後追加）
└── models/                 # モデルファイル置き場（git 管理外）
```

---

## セットアップ

### 1. リポジトリをクローン

```bash
git clone git@github.com:kaiKyutech/llama-server.git
cd llama-server
```

### 2. llama.cpp をビルド

```bash
chmod +x setup/install_llama.sh

# GPU を自動検出してビルド（推奨）
./setup/install_llama.sh

# GPU アーキテクチャを手動指定する場合
CUDA_ARCH=89 ./setup/install_llama.sh   # RTX 40xx
CUDA_ARCH=86 ./setup/install_llama.sh   # RTX 30xx
CUDA_ARCH=80 ./setup/install_llama.sh   # A100
CUDA_ARCH=0  ./setup/install_llama.sh   # CPU only
```

### 3. モデルを配置

```bash
mkdir -p models
# models/ に .gguf ファイルを手動で置く（git 管理外）
```

---

## 別サーバーへの展開

```bash
# 初回
git clone git@github.com:kaiKyutech/llama-server.git
cd llama-server
./setup/install_llama.sh

# 更新取り込み
git pull origin main
```
