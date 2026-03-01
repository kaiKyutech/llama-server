#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=1.0"]
# ///
"""
llama-server インタラクティブチャット

使い方:
  uv run scripts/chat.py
  uv run scripts/chat.py --url http://localhost:8080/v1
  uv run scripts/chat.py --system "あなたは優秀なアシスタントです"

終了: q, quit, exit または Ctrl+C
"""

import sys
import time
import argparse
from openai import OpenAI


def main():
    parser = argparse.ArgumentParser(description="llama-server インタラクティブチャット")
    parser.add_argument("--url", default="http://localhost:8080/v1", help="llama-server の URL (デフォルト: http://localhost:8080/v1)")
    parser.add_argument("--model", default="qwen3-vl-8b", help="モデル名 (デフォルト: qwen3-vl-8b)")
    parser.add_argument("--system", default="You are a helpful assistant.", help="システムプロンプト")
    args = parser.parse_args()

    client = OpenAI(base_url=args.url, api_key="dummy")
    history = [{"role": "system", "content": args.system}]

    print(f"接続先: {args.url}")
    print(f"モデル: {args.model}")
    print("終了: q または Ctrl+C")
    print("-" * 40)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n終了します")
            break

        if not user_input or user_input.lower() in ("q", "quit", "exit"):
            print("終了します")
            break

        history.append({"role": "user", "content": user_input})
        print("Assistant: ", end="", flush=True)

        start_time = None
        token_count = 0
        full_response = ""

        try:
            stream = client.chat.completions.create(
                model=args.model,
                messages=history,
                stream=True,
                stream_options={"include_usage": True},
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if start_time is None:
                        start_time = time.perf_counter()
                    print(content, end="", flush=True)
                    full_response += content

                # ストリーム末尾のチャンクに usage が含まれる
                if hasattr(chunk, "usage") and chunk.usage:
                    token_count = chunk.usage.completion_tokens or 0

        except KeyboardInterrupt:
            print("\n[中断]")
            history.pop()
            continue
        except Exception as e:
            print(f"\nエラー: {e}")
            history.pop()
            continue

        elapsed = time.perf_counter() - start_time if start_time else 0

        # usage が取れなかった場合は文字数から推定（参考値）
        if token_count == 0 and full_response:
            token_count = len(full_response) // 4

        if elapsed > 0 and token_count > 0:
            tps = token_count / elapsed
            print(f"\n[{token_count} tokens | {tps:.1f} tok/s | {elapsed:.2f}s]")
        else:
            print()

        history.append({"role": "assistant", "content": full_response})


if __name__ == "__main__":
    main()
