import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.generation_config_inspect import comparison_messages
from scripts.generation_config_inspect import read_gguf_sampling_metadata


def _gguf_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack("<Q", len(encoded)) + encoded


def _write_test_gguf(
    path: Path, metadata: dict[str, tuple[int, int | float | str]]
) -> None:
    content = bytearray(b"GGUF")
    content.extend(struct.pack("<IQQ", 3, 0, len(metadata)))
    formats = {5: "i", 6: "f"}
    for key, (value_type, value) in metadata.items():
        content.extend(_gguf_string(key))
        content.extend(struct.pack("<I", value_type))
        if value_type == 8:
            content.extend(_gguf_string(str(value)))
        else:
            content.extend(struct.pack(f"<{formats[value_type]}", value))
    path.write_bytes(content)


class GenerationConfigInspectTest(unittest.TestCase):
    def test_reads_sampling_metadata_without_tensor_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.gguf"
            _write_test_gguf(
                path,
                {
                    "general.sampling.top_k": (5, 64),
                    "general.sampling.top_p": (6, 0.95),
                    "general.sampling.sequence": (8, "top_k;top_p;temperature"),
                    "model.test": (5, 123),
                },
            )

            metadata = read_gguf_sampling_metadata(path)

        self.assertEqual(metadata["general.sampling.top_k"], 64)
        self.assertAlmostEqual(metadata["general.sampling.top_p"], 0.95, places=6)
        self.assertEqual(
            metadata["general.sampling.sequence"], "top_k;top_p;temperature"
        )
        self.assertNotIn("model.test", metadata)

    def test_warns_when_json_and_gguf_differ(self) -> None:
        messages = comparison_messages(
            {"temperature": 1.0, "top_k": 64},
            {
                "general.sampling.temp": 0.8,
                "general.sampling.top_k": 64,
            },
        )
        self.assertTrue(any("警告" in message and "temperature" in message for message in messages))
        self.assertFalse(any("警告" in message and "top_k" in message for message in messages))

    def test_reports_json_when_gguf_has_no_sampling_metadata(self) -> None:
        messages = comparison_messages({"temperature": 1.0}, {})
        self.assertTrue(any("generation_config.json の対応値" in message for message in messages))

    def test_reports_llama_defaults_when_both_are_missing(self) -> None:
        messages = comparison_messages(None, {})
        self.assertTrue(any("llama.cpp の既定値" in message for message in messages))

    def test_reports_gguf_when_json_is_missing(self) -> None:
        messages = comparison_messages(
            None, {"general.sampling.top_k": 64}
        )
        self.assertTrue(any("GGUF metadata を使用" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
