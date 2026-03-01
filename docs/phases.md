# フェーズ計画

## Phase 1 - llama.cpp ビルドと単体動作確認（★ 現在地）
- [ ] llama.cpp を CUDA 対応でビルド
- [ ] 8B モデル（GGUF）を GPU only でロードして動作確認
- [ ] OpenAI 互換 API で `curl` から叩けることを確認

## Phase 2 - モード切り替えとチューニング
- [ ] 27B モデルを CPU+GPU 混合でロード
- [ ] `--parallel` による並列スロットの調整
- [ ] スレッド数・バッチサイズのチューニング

## Phase 3 - Python ルーティングサーバー
- [ ] FastAPI で llama-server へのプロキシ実装
- [ ] 複数 llama-server プロセスのロードバランス

## Phase 4 - 外部公開
- [ ] Cloudflare Tunnel のセットアップ
- [ ] 認証（API キー等）の実装
