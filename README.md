# llama-server

llama.cpp の `llama-server` を推論バックエンドとして使い、Python でルーティング・管理を行うセルフホスト LLM サーバープロジェクト。
OpenAI 互換 API を提供しつつ、CPU / GPU / 混合推論に対応する。

## 目標

- **llama-server**（llama.cpp 組み込みサーバー）で OpenAI 互換 API を提供
- **Python サーバー**でルーティング・ロードバランス・認証を担当
- GPU only / CPU only / CPU+GPU 混合をコンフィグで切り替え可能
- **Cloudflare Tunnel (cloudflared)** で固定 IP なしに外部公開
- GitHub で管理し、異なるスペックのサーバーでも動作可能にする

## アーキテクチャ

```
[クライアント (curl / OpenAI SDK 等)]
        ↓ OpenAI 互換リクエスト (/v1/chat/completions 等)
[Python サーバー (FastAPI)]   ← ルーティング・認証・ロードバランス
        ↓
[llama-server × N プロセス]  ← llama.cpp ネイティブ、並列スロット対応
        ↓
[CUDA GPU / CPU / 混合オフロード]
```

### なぜ Python を挟むか
llama-server 単体でも `--parallel` で並列スロットは持てるが、
**複数プロセスをまたいだロードバランスや動的な起動・停止**は Python 層で管理する。

### llama-server が OpenAI 互換 API を提供する仕組み
llama.cpp の `llama-server` は以下のエンドポイントをネイティブで持つ：
- `GET  /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/embeddings`

---

## 開発環境・ターゲット環境

| 項目 | 開発（WSL2） | 本番（別サーバー） |
|------|-------------|-----------------|
| OS | Ubuntu on WSL2 | Linux |
| GPU | RTX 4070 Ti (VRAM 12GB) | 可変（CPU only も想定） |
| Backend | CUDA | CUDA / CPU only |
| Python | 3.10 以上 | 3.10 以上 |

---

## GPU / CPU モードの切り替え

llama-server の `--n-gpu-layers (-ngl)` で制御する：

| モード | オプション例 | 用途 |
|--------|------------|------|
| GPU only | `--n-gpu-layers 99` | VRAM に全層収まる 8B 程度 |
| CPU + GPU | `--n-gpu-layers 20` | 27B など VRAM に収まらないモデル |
| CPU only | `--n-gpu-layers 0` | GPU なし環境 |

---

## フェーズ計画

### Phase 1 - llama.cpp ビルドと単体動作確認（★ 現在地）
- [ ] llama.cpp を CUDA 対応でビルド
- [ ] 8B モデル（GGUF）を GPU only でロードして動作確認
- [ ] OpenAI 互換 API で `curl` から叩けることを確認

### Phase 2 - モード切り替えとチューニング
- [ ] 27B モデルを CPU+GPU 混合でロード
- [ ] `--parallel` による並列スロットの調整
- [ ] スレッド数・バッチサイズのチューニング

### Phase 3 - Python ルーティングサーバー
- [ ] FastAPI で llama-server へのプロキシ実装
- [ ] 複数 llama-server プロセスのロードバランス
- [ ] 起動スクリプトの整備

### Phase 4 - 外部公開
- [ ] Cloudflare Tunnel のセットアップ
- [ ] 認証（API キー等）の実装

---

## ディレクトリ構成（予定）

```
llama-server/
├── README.md
├── setup/
│   ├── install_llama.sh      # llama.cpp CUDA ビルド
│   └── install_deps.sh       # Python 依存関係
├── configs/
│   ├── gpu_only.sh           # llama-server 起動オプション: GPU only
│   ├── cpu_gpu.sh            # llama-server 起動オプション: CPU+GPU
│   └── cpu_only.sh           # llama-server 起動オプション: CPU only
├── server/
│   ├── main.py               # FastAPI ルーター
│   └── config.py             # 設定（モデルパス・ポート等）
├── cloudflare/
│   └── config.yml
├── models/                   # .gitignore 対象
└── scripts/
    ├── start.sh
    └── stop.sh
```

---

## 使用モデル形式

- **GGUF**（llama.cpp ネイティブ形式）
- Hugging Face の GGUF 版（Q4_K_M, Q5_K_M, Q8_0 等の量子化）を推奨

---

## デプロイ手順（別サーバーへの展開）

### 初回セットアップ
```bash
git clone https://github.com/kaiKyutech/llama-server.git
cd llama-server

# llama.cpp のビルド（GPU 自動検出）
chmod +x setup/install_llama.sh
./setup/install_llama.sh

# GPU 種別を手動指定する場合
# CUDA_ARCH=86 ./setup/install_llama.sh  # RTX 30xx
# CUDA_ARCH=80 ./setup/install_llama.sh  # A100
# CUDA_ARCH=0  ./setup/install_llama.sh  # CPU only

# モデルを配置
mkdir -p models
# models/ に .gguf ファイルを手動で置く（git 管理外）
```

### 更新の取り込み（開発側で push した後）
```bash
git pull origin main
```

### 開発側からの push（WSL 上での作業後）
```bash
git add .
git commit -m "変更内容のメモ"
git push origin main
```

---

## Git 管理ルール

| 対象 | 管理 |
|------|------|
| スクリプト・設定ファイル・ソースコード | Git 管理（コミット対象） |
| `models/`（.gguf ファイル） | **Git 管理外**（各サーバーで個別に配置） |
| `llama.cpp/`（ビルド済みバイナリ） | **Git 管理外**（各サーバーでビルド） |
| `.env`（APIキー等） | **Git 管理外** |

---

## メモ・決定事項

- Python から llama をライブラリインポートする形式は **使わない**（並列化の制約があるため）
- llama-server を別プロセスとして起動し、Python は HTTP で通信する
- `models/` は `.gitignore` に追加しコミットしない
- 別サーバーでコーディングエージェントが使えないため、WSL 上で実装して GitHub 経由で展開する
