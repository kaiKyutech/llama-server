#!/usr/bin/env python3
"""Convert supported Hugging Face generation_config.json fields to llama.cpp args."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


class GenerationConfigError(ValueError):
    pass


def _number(
    config: dict[str, Any],
    key: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> int | float | None:
    value = config.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GenerationConfigError(f"{key} must be a number")
    if not math.isfinite(value):
        raise GenerationConfigError(f"{key} must be finite")
    if minimum is not None and value < minimum:
        raise GenerationConfigError(f"{key} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise GenerationConfigError(f"{key} must be <= {maximum}")
    return value


def _integer(
    config: dict[str, Any],
    key: str,
    *,
    minimum: int | None = None,
) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise GenerationConfigError(f"{key} must be an integer")
    if minimum is not None and value < minimum:
        raise GenerationConfigError(f"{key} must be >= {minimum}")
    return value


def llama_args_from_config(config: dict[str, Any]) -> list[str]:
    if not isinstance(config, dict):
        raise GenerationConfigError("the JSON root must be an object")

    args: list[str] = []

    do_sample = config.get("do_sample")
    if do_sample is not None and not isinstance(do_sample, bool):
        raise GenerationConfigError("do_sample must be true or false")

    temperature = _number(config, "temperature", minimum=0)
    if do_sample is False:
        args.extend(("--temp", "0"))
    elif temperature is not None:
        args.extend(("--temp", str(temperature)))

    mappings = (
        ("--top-k", _integer(config, "top_k", minimum=0)),
        ("--top-p", _number(config, "top_p", minimum=0, maximum=1)),
        ("--min-p", _number(config, "min_p", minimum=0, maximum=1)),
        ("--typical", _number(config, "typical_p", minimum=0, maximum=1)),
        (
            "--repeat-penalty",
            _number(config, "repetition_penalty", minimum=0),
        ),
    )
    for flag, value in mappings:
        if value is not None:
            args.extend((flag, str(value)))

    suppress_tokens = config.get("suppress_tokens")
    if suppress_tokens is not None:
        if not isinstance(suppress_tokens, list):
            raise GenerationConfigError("suppress_tokens must be an array")
        for token_id in suppress_tokens:
            if isinstance(token_id, bool) or not isinstance(token_id, int) or token_id < 0:
                raise GenerationConfigError(
                    "suppress_tokens must contain non-negative integer token IDs"
                )
            args.extend(("--logit-bias", f"{token_id}-inf"))

    return args


def load_llama_args(path: Path) -> list[str]:
    try:
        with path.open(encoding="utf-8") as file:
            config = json.load(file)
    except OSError as exc:
        raise GenerationConfigError(f"cannot read file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise GenerationConfigError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    return llama_args_from_config(config)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        llama_args = load_llama_args(args.path)
    except GenerationConfigError as exc:
        print(f"generation_config error: {exc}", file=sys.stderr)
        return 1

    print("\n".join(llama_args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
