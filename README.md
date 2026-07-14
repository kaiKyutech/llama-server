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
│   ├── gpu_only.sample.sh      # GPU only モード設定サンプル
│   ├── cpu_only.sample.sh      # CPU only モード設定サンプル
│   └── cpu_gpu.sample.sh       # CPU+GPU 混合モード設定サンプル
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

### 再ビルド（ビルドエラー後やクリーンビルドしたい場合）

`llama.cpp` 本体は残したままビルドディレクトリだけ削除して再実行する。

```bash
rm -rf llama.cpp/build
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

`configs/*.sample.sh` をコピーして、Git 管理外のローカル設定を作成する。
**最低限 `MODEL_PATH` をモデルの実際のパスに合わせること。**

```bash
cp configs/gpu_only.sample.sh configs/gpu_only.sh
cp configs/cpu_only.sample.sh configs/cpu_only.sh
cp configs/cpu_gpu.sample.sh configs/cpu_gpu.sh
```

使うモードの設定だけ作成すればよい。`configs/gpu_only.sh`、`configs/cpu_only.sh`、
`configs/cpu_gpu.sh` は `.gitignore` 対象なので、サーバー固有のモデルパスや調整値を変更しても push されない。

```
configs/
├── gpu_only.sample.sh → gpu_only.sh   # GPU only
├── cpu_only.sample.sh → cpu_only.sh   # CPU only
└── cpu_gpu.sample.sh → cpu_gpu.sh     # CPU+GPU 混合
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
LOG_VERBOSITY=4 ./scripts/start.sh configs/cpu_gpu.sh # ログ出力
```

### MTP speculative decoding

MTPを使う場合は、主モデルと同じ系列・サイズに対応する assistant/MTP GGUF を設定する。
主モデルがQAT版なら、それに対応するMTPモデルを組み合わせる。対応しないモデル同士は混在させない。

```sh
MODEL_PATH="models/gemma4/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf"
MMPROJ_PATH="models/gemma4/mmproj-BF16.gguf"
SPEC_DRAFT_MODEL_PATH="models/gemma4/mtp-gemma-4-12B-it.gguf"
SPEC_TYPE="draft-mtp"
SPEC_DRAFT_N_MAX=3
SPEC_DRAFT_N_GPU_LAYERS=auto
```

`SPEC_DRAFT_N_MAX` は速度とドラフト受理率を見ながら調整する。まずは llama.cpp の既定値と同じ `3` を基準にし、
MTPなしの結果とも比較する。起動ログの `draft acceptance` で受理率を確認できる。

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

### 公式ツールで並列数を調べる

`setup/install_llama.sh` で `llama.cpp` をビルドすると、`llama.cpp/build/bin/` に公式ベンチツールも生成される。

```bash
ls llama.cpp/build/bin/llama-bench llama.cpp/build/bin/llama-batched-bench
```

#### `llama-bench` と `llama-batched-bench` の違い

- `llama-bench`: 単体の推論性能を測るツール
- `llama-batched-bench`: 複数系列を同時に流したときの性能を測るツール

`llama-bench` の `-pg` は **parallel の意味ではなく**、`prompt tokens, generated tokens` の組を表す。
サーバーの `PARALLEL` や `--parallel` の最適値を探したい場合は、基本的に `llama-batched-bench` を使う。

#### まず単体性能を見る

```bash
./llama.cpp/build/bin/llama-bench \
  -m models/qwen3.5/Qwen3.5-9B-UD-Q5_K_XL.gguf \
  -p 512 \
  -n 128
```

これは 1 リクエスト相当の prompt 処理速度と生成速度の目安を見るためのもの。

#### 並列数を変えて総スループットを測る

現在の `configs/cpu_gpu.sh` に近い条件で、並列数だけを変えて比較する例:

```bash
./llama.cpp/build/bin/llama-batched-bench \
  -m models/qwen3.5/Qwen3.5-9B-UD-Q5_K_XL.gguf \
  -c 8192 \
  -b 2048 \
  -ub 512 \
  -ngl auto \
  -npp 512 \
  -ntg 128 \
  -npl 1,2,4,8
```

主な引数:

- `-c`: 総コンテキスト長。サーバーの `CTX_SIZE` に相当
- `-npp`: 1リクエストあたりの prompt トークン数
- `-ntg`: 1リクエストあたりの生成トークン数
- `-npl`: 試したい並列数。サーバーの `PARALLEL` に相当

出力では次を見る:

- `S t/s`: 全体の総スループット。複数リクエストを同時にさばく用途ではこれを重視
- `S_TG t/s`: 生成フェーズの総トークン速度
- `N_KV`: 必要な KV キャッシュ量の目安

`S t/s` が最大になる `-npl` が、現在のモデル・量子化・GPU 条件での有力候補になる。
ただし並列数を増やしすぎると 1 リクエストあたりの体感速度や各スロットのコンテキスト長は悪化するため、最大値だけでなく用途も合わせて判断すること。

#### 調査の進め方

1. `-npl 1,2,4,8` で大まかな傾向を見る
2. まだ `S t/s` が伸びるなら `-npl 10,12` のように上側を追加で試す
3. VRAM や KV キャッシュが厳しい場合は `-c` を下げるか `-npp` / `-ntg` を小さくする
4. 実運用に近い prompt 長で再測定する

異なるユーザーが別々の prompt を投げる通常のサーバー用途では、まず `-pps` は付けずに測るのが無難。
共通の長い system prompt を多数の系列で共有したい場合だけ `-pps` も比較対象にする。

---

## thinking モードの制御（Qwen3 等）

サーバー起動時に決まり、全クライアントに一律適用される。クライアント側での指定は不要。

`configs/*.sh` の思考モードセクションで設定する：

```sh
# thinking ON
CHAT_TEMPLATE_KWARGS='{"enable_thinking": true}'

# thinking OFF
REASONING_BUDGET=0
```

両方コメントアウトのままだとモデルによって動作が変わるため、どちらかを明示的に指定することを推奨。

thinking が有効な場合、レスポンスの `reasoning_content` フィールドに思考過程が流れてくる。

---

## Cloudflare トンネル（外部公開）

llama-server とは独立して起動する。llama-server を再起動してもトンネルは維持される。

### cloudflared のインストール

**sudo が使える環境：**

```bash
curl -L -o cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

**sudo が使えない環境（JupyterHub 等）：**

```bash
mkdir -p ~/bin
curl -L -o ~/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x ~/bin/cloudflared
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
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
# configs/*.sample.sh をコピーし、作成したローカル設定を環境に合わせて編集

# 更新取り込み
git pull origin main
```
