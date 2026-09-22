# OpenCodeとOpenClawの比較

更新日: 2026-08-10

## 結論

指定したプロジェクトフォルダを開き、その中で対話しながら調査・編集する用途には、OpenCodeのほうが適している。

OpenClawは、単一の作業フォルダを都度開くツールというより、専用ワークスペース、長期記憶、定期実行、通知などを備えた常駐型の個人AIエージェントに近い。

R2V向けプロンプト生成では、現状のOpenCode UIがMP4を直接添付できない点だけが問題になる。OpenCodeからOpenClawへ全面移行するより、OpenCodeにllama.cppの動画入力を呼び出す専用ツールを追加する構成が最も用途に合う。

## 主な違い

| 観点 | OpenCode | OpenClaw |
|---|---|---|
| 基本的な役割 | プロジェクト単位で使う対話型エージェント | 常駐型の個人AI・自動化基盤 |
| 作業場所 | 起動時に対象フォルダを指定する | エージェントごとに専用workspaceを持つ |
| コーディング | Git、差分、検索、編集などに強い | 可能だが開発作業だけに特化していない |
| コード以外の作業 | ファイル整理、文章生成、データ処理にも利用できる | 長期記憶や外部連携を含む継続作業に強い |
| MP4入力 | 現行の添付UIでは非対応 | 動画のMedia Understandingを持つ |
| ローカルllama.cpp | OpenAI互換APIとして接続しやすい | カスタムOpenAI互換プロバイダーとして接続可能 |
| llama.cpp固有の動画入力 | 標準UIからは送れず、専用ツール等が必要 | 自動変換される保証はなく、専用アダプター等が必要 |
| 権限管理 | ask、allow、denyとプロジェクト外アクセスの制御 | workspace制限、ツール制限、sandboxなど。高機能だが複雑 |
| 長期記憶 | 主にプロジェクトとセッション単位 | MEMORY.mdや日次メモを標準的に利用する |
| 自動化 | ユーザーが起動して対話的に使う用途が中心 | 定期実行、常駐処理、メッセージ受信、通知に向く |
| 導入の重さ | 比較的軽い | Gateway、workspace、sandbox等の設計が必要 |

## プロジェクトフォルダを指定する場合

### OpenCode

OpenCodeは対象フォルダを直接指定して起動できる。

~~~powershell
opencode "C:\Users\kaiha\personal-files\R2V-project"
~~~

Gitリポジトリやソースコードだけでなく、次のような非コーディング中心のフォルダでも使用できる。

~~~text
R2V-project/
├─ videos/
├─ prompts/
├─ outputs/
├─ templates/
├─ AGENTS.md
└─ generation-rules.md
~~~

AGENTS.mdには、例えば次のように作業規則を記載する。

~~~markdown
このプロジェクトでは、videos内の参照動画を分析し、
R2V向けプロンプトをpromptsへ保存する。
元の動画と既存プロンプトは変更しない。
~~~

OpenCodeには、プロジェクト外のファイルアクセスを制御するexternal_directory権限がある。読み取り、編集、シェル実行などもask、allow、denyで制御できる。

### OpenClaw

OpenClawでもエージェントごとにworkspaceを指定できる。ただしworkspaceは単なるカレントディレクトリではなく、そのエージェントのホームに近い。

代表的な構成は次のとおり。

~~~text
AGENTS.md
SOUL.md
USER.md
TOOLS.md
MEMORY.md
memory/
skills/
~~~

OpenClawは、人格、ユーザー情報、ツールの使い方、長期記憶、日ごとの記録をworkspaceに保持する。既存プロジェクトをworkspaceに指定することも可能だが、OpenClaw自身の管理ファイルがプロジェクト内に増える可能性を考慮する必要がある。

## 動画入力

### OpenCodeの現状

OpenCodeの内部モデル定義はvideoモダリティを表現できるが、現行のDesktop/App UIが添付対象として許可しているのは主に画像、PDF、テキストファイルである。MP4は添付UIの許可リストに含まれず、動画をドロップしてもモデルへ届かない。

FFmpegをインストールしても、このUI制限そのものは解除されない。FFmpegは動画から静止画を抽出するカスタムツールなどには利用できる。

### OpenClawの現状

OpenClawには、受信した画像、音声、動画を応答処理前に解析するMedia Understandingがある。動画の標準プロバイダー統合は主にGoogle、Qwen、Moonshot向けである。

ローカルのllama.cppをカスタムOpenAI互換プロバイダーとして登録することは可能だが、llama.cpp固有のinput_videoリクエストへ自動変換されるとは限らない。現在のGemma 4とllama.cppを動画解析に使うには、OpenClaw側でもCLIフォールバック、プラグイン、専用アダプター等が必要になる可能性が高い。

## R2V向けの推奨構成

### 対話的に作業する場合

OpenCodeをプロジェクトエージェントとして使い、プロジェクトローカルのvideo_to_promptツールを追加する。

~~~text
OpenCode
  ├─ 指定フォルダ内の検索・読み書き
  ├─ 必要に応じたコード編集
  └─ video_to_prompt
       └─ llama.cppのinput_videoへMP4を送信
~~~

想定する依頼例:

~~~text
videos/sample.mp4を解析して、R2V用プロンプトを
prompts/sample.mdに保存してください。
既存ファイルは上書きしないでください。
~~~

この構成では役割を次のように分離できる。

- 動画解析: llama.cppとGemma 4
- プロジェクト内の作業: OpenCode
- ファイル操作の承認: OpenCode
- 動画API形式への変換: video_to_promptツール

### 自動処理へ発展させる場合

次の要件が必要になった段階ではOpenClawが有力になる。

- videosへの新規MP4追加を監視する
- 複数動画を定期的にバッチ処理する
- 処理履歴や好みを長期記憶する
- 完了時にDiscord等へ通知する
- 人が起動しなくても常駐して処理する

その場合も、ローカルllama.cppの動画APIを呼ぶ専用アダプターは別途必要になる可能性がある。

## llama.cpp公式Web UIという選択肢

最新のllama.cpp Web UIは動画入力に加え、実験的な組み込みファイルツールも提供している。ただしOpenCodeほどプロジェクト管理や権限確認が成熟していない。

単発で動画からプロンプトを生成するだけなら公式Web UIが最短である。指定フォルダ内で継続的に作業したり、コードやGitも扱ったりする場合はOpenCodeのほうが扱いやすい。

組み込みツールを有効にする場合、--tools allや--agentはシェル実行まで許可する。外部公開しているサーバーでは有効にせず、ローカル専用設定とAPI公開設定を分離する。

## 選択基準

- 人がプロジェクトを開き、内容を確認しながら作業させる: OpenCode
- MP4を単発で解析してプロンプトを得る: llama.cpp公式Web UI
- OpenCode内で動画解析とファイル作業を一体化する: OpenCode + 専用カスタムツール
- フォルダ監視、定期実行、通知、長期記憶まで自動化する: OpenClaw

## 参考資料

- [OpenCode: Intro](https://opencode.ai/docs/)
- [OpenCode: Agents and permissions](https://opencode.ai/docs/agents/)
- [OpenCode: Custom Tools](https://opencode.ai/docs/custom-tools/)
- [OpenCode: file picker source](https://github.com/anomalyco/opencode/blob/dev/packages/app/src/constants/file-picker.ts)
- [OpenClaw: Agent workspace](https://docs.openclaw.ai/concepts/agent-workspace)
- [OpenClaw: Media Understanding](https://docs.openclaw.ai/nodes/media-understanding)
- [OpenClaw: Local models](https://docs.openclaw.ai/gateway/local-models)
- [llama.cpp: llama-server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
