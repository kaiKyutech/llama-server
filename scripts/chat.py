#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.25"]
# ///
"""
llama-server インタラクティブチャット

使い方:
  uv run scripts/chat.py
  uv run scripts/chat.py --url http://localhost:8080
  uv run scripts/chat.py --system "あなたは優秀なアシスタントです"

終了: q, quit, exit または Ctrl+C
"""

import json
import time
import argparse
import httpx


def chat_once(client: httpx.Client, url: str, model: str, messages: list) -> tuple[str, int, float]:
    """1回の応答をストリーミングで受け取り (full_response, token_count, elapsed) を返す"""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    start_time = None
    token_count = 0
    full_response = ""
    thinking_started = False
    thinking_ended = False

    DIM = "\033[2m"
    RESET = "\033[0m"

    with client.stream("POST", f"{url}/v1/chat/completions", json=payload, timeout=300.0) as response:
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})

                reasoning = delta.get("reasoning_content", "")
                if reasoning:
                    if not thinking_started:
                        print(f"{DIM}[thinking]{RESET}", flush=True)
                        thinking_started = True
                    print(f"{DIM}{reasoning}{RESET}", end="", flush=True)

                content = delta.get("content", "")
                if content:
                    if thinking_started and not thinking_ended:
                        print(f"\n{DIM}[/thinking]{RESET}\n", flush=True)
                        thinking_ended = True
                    if start_time is None:
                        start_time = time.perf_counter()
                    print(content, end="", flush=True)
                    full_response += content

            # ストリーム末尾のチャンクに usage が含まれる
            usage = chunk.get("usage")
            if usage:
                token_count = usage.get("completion_tokens", 0)

    elapsed = time.perf_counter() - start_time if start_time else 0
    return full_response, token_count, elapsed


def get_model_name(client: httpx.Client, url: str, fallback: str) -> str:
    """サーバーから実際のモデル名を取得する"""
    try:
        resp = client.get(f"{url}/v1/models", timeout=5.0)
        models = resp.json().get("data", [])
        if models:
            return models[0].get("id", fallback)
    except Exception:
        pass
    return fallback


def main():
    parser = argparse.ArgumentParser(description="llama-server インタラクティブチャット")
    parser.add_argument("--url", default="http://localhost:8080", help="llama-server の URL (デフォルト: http://localhost:8080)")
    parser.add_argument("--model", default=None, help="モデル名（省略時はサーバーから自動取得）")
    parser.add_argument("--system", default="You are a helpful assistant.", help="システムプロンプト")
    args = parser.parse_args()

    history = [{"role": "system", "content": args.system}]

    with httpx.Client() as client:
        model = args.model or get_model_name(client, args.url, "default")

        print(f"接続先: {args.url}")
        print(f"モデル: {model}")
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

            try:
                full_response, token_count, elapsed = chat_once(client, args.url, model, history)
            except KeyboardInterrupt:
                print("\n[中断]")
                history.pop()
                continue
            except Exception as e:
                print(f"\nエラー: {e}")
                history.pop()
                continue

            if elapsed > 0 and token_count > 0:
                tps = token_count / elapsed
                print(f"\n[{token_count} tokens | {tps:.1f} tok/s | {elapsed:.2f}s]")
            else:
                print()

            history.append({"role": "assistant", "content": full_response})


if __name__ == "__main__":
    main()
