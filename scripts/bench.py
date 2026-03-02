#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.25"]
# ///
"""
llama-server 並列ベンチマーク
複数セッションを同時に投げてトークン速度を計測する。

使い方:
  uv run scripts/bench.py
  uv run scripts/bench.py --sessions 4 --prompt "日本の歴史について説明して"
  uv run scripts/bench.py --sessions 8 --url http://localhost:8080

出力:
  セッションごとのトークン数・時間・tok/s
  全体の合計スループット（tok/s）
"""

import asyncio
import json
import time
import argparse
import httpx

DEFAULT_PROMPT = "日本の四季について200文字程度で説明してください。"


async def single_session(
    client: httpx.AsyncClient,
    session_id: int,
    url: str,
    model: str,
    prompt: str,
) -> dict:
    """1セッション分のリクエストを実行し、計測結果を返す"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    start_time = None
    token_count = 0
    char_count = 0

    try:
        async with client.stream(
            "POST",
            f"{url}/v1/chat/completions",
            json=payload,
            timeout=120.0,
        ) as response:
            async for line in response.aiter_lines():
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
                    content = choices[0].get("delta", {}).get("content", "")
                    if content:
                        if start_time is None:
                            start_time = time.perf_counter()
                        char_count += len(content)

                # ストリーム末尾に usage が含まれる
                usage = chunk.get("usage")
                if usage:
                    token_count = usage.get("completion_tokens", 0)

        elapsed = time.perf_counter() - start_time if start_time else 0

        # usage が取れなかった場合は文字数から推定
        if token_count == 0:
            token_count = char_count // 4

        tps = token_count / elapsed if elapsed > 0 else 0
        return {
            "session": session_id,
            "tokens": token_count,
            "elapsed": elapsed,
            "tps": tps,
            "error": None,
        }

    except Exception as e:
        return {
            "session": session_id,
            "tokens": 0,
            "elapsed": 0,
            "tps": 0,
            "error": str(e),
        }


async def run_bench(url: str, model: str, sessions: int, prompt: str):
    print(f"ベンチマーク開始")
    print(f"  URL      : {url}")
    print(f"  モデル   : {model}")
    print(f"  並列数   : {sessions}")
    print(f"  プロンプト: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
    print()

    start_all = time.perf_counter()

    async with httpx.AsyncClient() as client:
        tasks = [
            single_session(client, i + 1, url, model, prompt)
            for i in range(sessions)
        ]
        results = await asyncio.gather(*tasks)

    total_elapsed = time.perf_counter() - start_all

    # 結果表示
    print(f"{'Session':>8} | {'Tokens':>8} | {'Time(s)':>8} | {'tok/s':>8}")
    print("-" * 46)

    valid = [r for r in results if r["error"] is None]

    for r in sorted(results, key=lambda x: x["session"]):
        if r["error"]:
            print(f"{r['session']:>8} | エラー: {r['error']}")
        else:
            print(f"{r['session']:>8} | {r['tokens']:>8} | {r['elapsed']:>8.2f} | {r['tps']:>8.1f}")

    if valid:
        avg_tps = sum(r["tps"] for r in valid) / len(valid)
        total_tokens = sum(r["tokens"] for r in valid)
        print("-" * 46)
        print(f"{'平均':>8} | {total_tokens // len(valid):>8} | {total_elapsed:>8.2f} | {avg_tps:>8.1f}")
        print()
        print(f"合計トークン数 : {total_tokens}")
        print(f"全体時間       : {total_elapsed:.2f}s")
        print(f"総スループット : {total_tokens / total_elapsed:.1f} tok/s")


def get_model_name(url: str, fallback: str) -> str:
    """サーバーから実際のモデル名を取得する"""
    try:
        resp = httpx.get(f"{url}/v1/models", timeout=5.0)
        models = resp.json().get("data", [])
        if models:
            return models[0].get("id", fallback)
    except Exception:
        pass
    return fallback


def main():
    parser = argparse.ArgumentParser(description="llama-server 並列ベンチマーク")
    parser.add_argument("--url", default="http://localhost:8080", help="llama-server の URL (デフォルト: http://localhost:8080)")
    parser.add_argument("--model", default=None, help="モデル名（省略時はサーバーから自動取得）")
    parser.add_argument("--sessions", type=int, default=4, help="並列セッション数 (デフォルト: 4)")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="テスト用プロンプト")
    args = parser.parse_args()

    model = args.model or get_model_name(args.url, "default")
    asyncio.run(run_bench(args.url, model, args.sessions, args.prompt))


if __name__ == "__main__":
    main()
