#!/usr/bin/env python3
"""Report how generation defaults are selected from JSON, GGUF, or llama.cpp."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any, BinaryIO


class GGUFMetadataError(ValueError):
    pass


_GGUF_TYPES = {
    0: ("B", 1),
    1: ("b", 1),
    2: ("H", 2),
    3: ("h", 2),
    4: ("I", 4),
    5: ("i", 4),
    6: ("f", 4),
    7: ("?", 1),
    10: ("Q", 8),
    11: ("q", 8),
    12: ("d", 8),
}
_GGUF_TYPE_STRING = 8
_GGUF_TYPE_ARRAY = 9

_JSON_GGUF_FIELDS = (
    ("temperature", "general.sampling.temp"),
    ("top_k", "general.sampling.top_k"),
    ("top_p", "general.sampling.top_p"),
    ("min_p", "general.sampling.min_p"),
    ("repetition_penalty", "general.sampling.penalty_repeat"),
)


def _read_exact(file: BinaryIO, size: int) -> bytes:
    data = file.read(size)
    if len(data) != size:
        raise GGUFMetadataError("unexpected end of GGUF metadata")
    return data


def _uint32(file: BinaryIO) -> int:
    return struct.unpack("<I", _read_exact(file, 4))[0]


def _uint64(file: BinaryIO) -> int:
    return struct.unpack("<Q", _read_exact(file, 8))[0]


def _string(file: BinaryIO) -> str:
    size = _uint64(file)
    try:
        return _read_exact(file, size).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GGUFMetadataError("invalid UTF-8 in GGUF metadata") from exc


def _skip_value(file: BinaryIO, value_type: int) -> None:
    if value_type in _GGUF_TYPES:
        file.seek(_GGUF_TYPES[value_type][1], 1)
        return
    if value_type == _GGUF_TYPE_STRING:
        file.seek(_uint64(file), 1)
        return
    if value_type == _GGUF_TYPE_ARRAY:
        item_type = _uint32(file)
        count = _uint64(file)
        if item_type in _GGUF_TYPES:
            file.seek(_GGUF_TYPES[item_type][1] * count, 1)
            return
        for _ in range(count):
            _skip_value(file, item_type)
        return
    raise GGUFMetadataError(f"unsupported GGUF value type: {value_type}")


def _read_metadata_value(
    file: BinaryIO, value_type: int
) -> int | float | bool | str:
    if value_type in _GGUF_TYPES:
        format_code, size = _GGUF_TYPES[value_type]
        return struct.unpack(f"<{format_code}", _read_exact(file, size))[0]
    if value_type == _GGUF_TYPE_STRING:
        return _string(file)
    raise GGUFMetadataError(
        f"unsupported general.sampling GGUF type: {value_type}"
    )


def read_gguf_sampling_metadata(
    path: Path,
) -> dict[str, int | float | bool | str]:
    metadata: dict[str, int | float | bool | str] = {}
    try:
        with path.open("rb") as file:
            if _read_exact(file, 4) != b"GGUF":
                raise GGUFMetadataError("not a GGUF file")
            version = _uint32(file)
            if version not in (2, 3):
                raise GGUFMetadataError(f"unsupported GGUF version: {version}")

            _uint64(file)  # tensor count
            metadata_count = _uint64(file)
            for _ in range(metadata_count):
                key = _string(file)
                value_type = _uint32(file)
                if key.startswith("general.sampling."):
                    metadata[key] = _read_metadata_value(file, value_type)
                else:
                    _skip_value(file, value_type)
    except OSError as exc:
        raise GGUFMetadataError(f"cannot read GGUF metadata: {exc}") from exc
    return metadata


def load_generation_config(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as file:
            value = json.load(file)
    except OSError as exc:
        raise ValueError(f"cannot read generation_config.json: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid generation_config.json at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError("generation_config.json root must be an object")
    return value


def effective_json_values(config: dict[str, Any]) -> dict[str, int | float]:
    values: dict[str, int | float] = {}
    if config.get("do_sample") is False:
        values["temperature"] = 0
    elif isinstance(config.get("temperature"), (int, float)) and not isinstance(
        config.get("temperature"), bool
    ):
        values["temperature"] = config["temperature"]

    for key in ("top_k", "top_p", "min_p", "repetition_penalty"):
        value = config.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values[key] = value
    return values


def comparison_messages(
    config: dict[str, Any] | None,
    gguf_metadata: dict[str, int | float | bool | str],
) -> list[str]:
    messages: list[str] = []
    gguf_summary = ", ".join(
        f"{key.removeprefix('general.sampling.')}={value}"
        for key, value in sorted(gguf_metadata.items())
    )

    if config is None:
        if gguf_metadata:
            messages.append(
                "生成設定: generation_config.json は未指定です。"
                f"GGUF metadata を使用します（{gguf_summary}）。"
                "未設定項目は llama.cpp の既定値です。"
            )
        else:
            messages.append(
                "生成設定: generation_config.json と GGUF general.sampling.* が"
                "ないため、llama.cpp の既定値を使用します。"
            )
        return messages

    json_values = effective_json_values(config)
    if gguf_metadata:
        messages.append(
            "生成設定: generation_config.json を優先します。"
            f"GGUF metadata も検出しました（{gguf_summary}）。"
        )
        for json_key, gguf_key in _JSON_GGUF_FIELDS:
            if json_key not in json_values or gguf_key not in gguf_metadata:
                continue
            json_value = json_values[json_key]
            gguf_value = gguf_metadata[gguf_key]
            if not math.isclose(
                float(json_value), float(gguf_value), rel_tol=1e-6, abs_tol=1e-6
            ):
                messages.append(
                    "警告: "
                    f"generation_config.json の {json_key}={json_value} は "
                    f"GGUF の {gguf_key}={gguf_value} と異なります。"
                    "generation_config.json の値を使用します。"
                )
        messages.append(
            "生成設定: JSONにない項目はGGUF metadata、"
            "どちらにもない項目はllama.cppの既定値を使用します。"
        )
    elif json_values:
        messages.append(
            "生成設定: GGUF general.sampling.* がないため、"
            "generation_config.json の対応値を使用します。"
            "JSONにない項目はllama.cppの既定値です。"
        )
    else:
        messages.append(
            "生成設定: GGUF general.sampling.* がなく、generation_config.json にも"
            "対応するsampling項目がないため、llama.cppの既定値を使用します。"
        )
    return messages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--generation-config", type=Path)
    args = parser.parse_args()

    try:
        metadata = read_gguf_sampling_metadata(args.model)
        config = (
            load_generation_config(args.generation_config)
            if args.generation_config
            else None
        )
    except (GGUFMetadataError, ValueError) as exc:
        print(f"生成設定の確認エラー: {exc}", file=sys.stderr)
        return 1

    for message in comparison_messages(config, metadata):
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
