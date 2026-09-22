# このPCでのローカルLLM運用

## 正式な作業場所

- WSL ディストリビューション: `Ubuntu-24.04`
- このプロジェクト: `/home/akai/llama-server`
- モデル: `/home/akai/llama-server/models`
- ローカル設定: `/home/akai/llama-server/configs/*.sh`（sample以外はGit管理外）
- 通常版エンジン: `/home/akai/llama-server/llama.cpp/build/bin/llama-server`
- bonsai: `/home/akai/bonsai`（独立したプロジェクト。エンジンも共有しない）

Windows側の `C:\Users\kaiha\personal-files\akai_project\llama-server` は移行前の保管用コピー。
以後の編集・Git操作・モデル追加はUbuntu側で行う。旧コピーのモデルは移行済みのため、旧ランチャーを使わない。
これらはこのPCの配置であり、別サーバーでは配置を自由に変更できる。

## 起動（ユーザーから起動を依頼されたときのみ）

まず `ss -ltnp 'sport = :8080'` で利用状況を確認する。
8080が使用中なら起動せず、稼働中のbonsai等を停止・置換しない。
2026-09-22の移行作業では起動確認を行わず、既存のbonsaiを稼働させたままにする。

Ubuntu:

```bash
cd /home/akai/llama-server
bash scripts/start.sh configs/cpu_gpu.sh
```

Windows PowerShell（Ubuntu側の同じプロジェクトを起動）:

```powershell
wsl -d Ubuntu-24.04 --cd /home/akai/llama-server bash scripts/start.sh configs/cpu_gpu.sh
```

設定を変える場合は `configs/gpu_only.sh` などを選ぶ。
移行時点の `configs/cpu_only.sh` は未配置のQwen3-VLモデルを参照しているため、使用前にモデル配置または設定変更が必要。
停止は起動したターミナルでCtrl+C。名前だけで一括killするとbonsaiも対象になり得るため行わない。

## 利用側

`llm-bench` と `subs-llmapi` はHTTP経由で接続する。
通常の接続先は `http://127.0.0.1:8080`（OpenAI互換APIは `/v1`）。
エンジンを利用側プロジェクトへコピーする必要はない。
bonsaiと通常版を切り替える場合、現在のサーバー停止はユーザーの指示を確認して行う。

## Gitとエンジン

GitHubは運用スクリプトと文書を管理する。モデル、ローカル設定、llama.cppはcloneだけでは復元されない。
移行時は通常版llama.cppの既存コミット `74ce15741` を維持する。
ビルドディレクトリには絶対パスが含まれるため、Ubuntuの新しい配置で再ビルドする。
更新と移行は分け、動作確認前にエンジンを最新版へ更新しない。
