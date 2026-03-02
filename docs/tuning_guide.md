# チューニングガイド

---

## 起動直後に確認すべきログ

起動時に出力されるログで、設定が意図通りになっているかを必ず確認する。

### GPU にちゃんと載っているか

```
load_tensors: offloaded 37/37 layers to GPU   ← 全層 GPU に載った
load_tensors:        CUDA0 model buffer size =  4455.34 MiB   ← GPU 使用量
load_tensors:   CPU_Mapped model buffer size =   333.84 MiB   ← これは mmap（正常）
```

`offloaded N/M layers` の N と M が一致していれば GPU only。
N < M の場合は CPU+GPU 混合になっている。

### VRAM が足りずにコンテキストが削られていないか

```
llama_params_fit_impl: projected to use 42143 MiB vs. 11036 MiB free
llama_params_fit_impl: context size reduced from 262144 to 36864   ← 自動削減
```

このログが出た場合、コンテキスト長が自動で短縮されている。
意図していなければ `CTX_SIZE` を明示的に小さく指定して VRAM の余裕を作る。

### 並列スロット数とコンテキスト長

```
main: n_parallel is set to auto, using n_parallel = 4
slot load_model: id 0 | new slot, n_ctx = 36864
```

`n_parallel` と `n_ctx` の積が総コンテキスト容量。
VRAM に対してこの値が大きすぎると自動削減が発生する。

### Flash Attention が有効になっているか

```
sched_reserve: Flash Attention was auto, set to enabled
```

`enabled` になっていれば OK。GPU 推論では基本的に有効になる。

### 層数の確認

```
print_info: n_layer = 36   ← このモデルは 36 層
```

`N_GPU_LAYERS` を設定する際の上限値として使う。
この値より大きい数を指定すれば全層 GPU になる。

---

## 1リクエストだけ処理できればいい場合

**目的：** 応答速度（1リクエストあたりの tok/s）を最大化する。

**設定の方針：**
- `PARALLEL=1` にしてスロットを1つに絞る
- その分 `CTX_SIZE` を大きく取れる
- KV キャッシュを全部1つのリクエストに使えるので長い会話に強い

```sh
PARALLEL=1
# CTX_SIZE はコメントを外さず auto に任せる（VRAM をフルに使う）
```

**確認指標：** `bench.py --sessions 1` の tok/s

---

## 複数リクエストを同時にさばきたい場合

**目的：** 総スループット（全セッション合計の tok/s）を最大化する。

**設定の方針：**
- `PARALLEL` を増やす（4, 8, 16 と試す）
- 並列数を増やすと1スロットあたりの `CTX_SIZE` が自動で縮む
- `CTX_SIZE` を明示的に小さく設定することでさらに並列数を増やせる

```sh
PARALLEL=8
CTX_SIZE=4096   # 1会話あたりのコンテキストを短くする代わりに並列数を増やす
```

**トレードオフ：**

| 並列数 | 1リクエストの速度 | 総スループット | コンテキスト長 |
|--------|-----------------|--------------|--------------|
| 1 | 最速 | 低い | 最大 |
| 4 | やや遅い | 中程度 | 中程度 |
| 8 | 遅い | 高い | 短い |

**確認指標：** `bench.py --sessions N` の「総スループット」

```bash
# 並列数を変えながら総スループットを比較する
uv run scripts/bench.py --sessions 1
uv run scripts/bench.py --sessions 4
uv run scripts/bench.py --sessions 8
```

---

## GPU only の塩梅

**前提：** モデル全体が VRAM に収まること。

**目安（VRAM 12GB の場合）：**

| モデルサイズ | 量子化 | VRAM 目安 | 可否 |
|------------|--------|----------|------|
| 8B | Q4_K_M | ~5GB | ○ |
| 8B | Q8_0 | ~9GB | ○ |
| 14B | Q4_K_M | ~9GB | ○ |
| 27B | Q4_K_M | ~17GB | ✗ |

**チューニングのポイント：**

1. まず `N_GPU_LAYERS=999`（全層 GPU）で起動
2. 起動ログで `offloaded N/N layers` を確認
3. VRAM に余裕があれば `CACHE_TYPE_K` / `CACHE_TYPE_V` を `f16`（デフォルト）のまま
4. VRAM がギリギリなら KV キャッシュを量子化して節約

```sh
# KV キャッシュを量子化して VRAM を節約（品質はほぼ変わらない）
CACHE_TYPE_K="q8_0"
CACHE_TYPE_V="q8_0"
```

**確認するログ：**
```
CUDA0 KV buffer size = 5184.00 MiB   ← KV キャッシュの VRAM 使用量
CUDA0 model buffer size = 4455.34 MiB  ← モデル本体の VRAM 使用量
```

---

## CPU only の塩梅

**前提：** GPU がない環境、または GPU を使わず動かしたい場合。

**チューニングのポイント：**

1. `N_GPU_LAYERS=0` で全層 CPU に
2. `THREADS` を論理コア数に合わせる（`nproc` コマンドで確認）
3. `MLOCK=true` でモデルを RAM に固定（スワップ防止）
4. 並列数は増やさず `PARALLEL=1` か `2` 程度にとどめる

```sh
N_GPU_LAYERS=0
THREADS=16        # nproc の出力に合わせる
MLOCK=true
PARALLEL=1
```

**確認コマンド：**
```bash
nproc   # 論理コア数を確認
```

**注意：** CPU only は GPU に比べて大幅に遅い（5〜10倍程度）。
ただし RAM が大きければ 27B や 70B など大型モデルも動かせる。

---

## CPU+GPU 混合の塩梅

**目的：** VRAM に収まらない大型モデルを GPU と CPU に分散して動かす。

**仕組み：**
- `N_GPU_LAYERS=N` で先頭 N 層を GPU、残りを CPU で処理
- 層が多いほど GPU で処理 → 速いが VRAM を消費
- 層が少ないほど CPU で処理 → 遅いが VRAM を節約

**最適な `N_GPU_LAYERS` の探し方：**

1. 起動ログで `n_layer = N` を確認（モデルの総層数）
2. まず半分の層数で起動してみる
3. VRAM に余裕があれば増やす、OOM エラーが出たら減らす

```bash
# 27B モデル（62層）の例
# まず 30 層から試す
N_GPU_LAYERS=30

# VRAM に余裕があれば増やす
N_GPU_LAYERS=45

# OOM になったら減らす
N_GPU_LAYERS=20
```

**OOM（VRAM 不足）エラーのサイン：**
```
CUDA error: out of memory
# または起動時にクラッシュ
```

**バランスの目安（VRAM 12GB で 27B Q4_K_M の場合）：**

| N_GPU_LAYERS | VRAM 使用量 | 速度感 |
|-------------|-----------|--------|
| 10 | ~4GB | CPU メイン（遅い） |
| 25 | ~8GB | バランス |
| 40 | ~12GB | GPU メイン（速い） |

**KV キャッシュもオフロードされる点に注意：**
KV キャッシュは VRAM に載る。コンテキストが長いと KV キャッシュが大きくなり VRAM を圧迫する。
コンテキストを短くするか `CACHE_TYPE_K="q8_0"` で削減する。

**確認指標：** `bench.py --sessions 1` の tok/s を `N_GPU_LAYERS` を変えながら比較

```bash
# N_GPU_LAYERS を変えながら速度を記録する
N_GPU_LAYERS=10  ./scripts/start.sh configs/cpu_gpu.sh &
uv run scripts/bench.py --sessions 1
```

---

## よくあるトラブルと確認箇所

| 症状 | 確認するログ・箇所 |
|------|-----------------|
| 起動しない | `エラー: モデルファイルが見つかりません` → `MODEL_PATH` を確認 |
| VRAM 不足でクラッシュ | `CUDA error: out of memory` → `N_GPU_LAYERS` を減らす |
| 遅い（GPU なのに） | `offloaded N/M` の N < M → `N_GPU_LAYERS` を増やす |
| コンテキストが短い | `context size reduced` → `CTX_SIZE` を明示指定するか並列数を減らす |
| tok/s が想定より低い | `n_parallel` を確認、並列数が多すぎると1リクエストが遅くなる |
