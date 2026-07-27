import json
import tempfile
import unittest
from pathlib import Path

from scripts.generation_config_args import GenerationConfigError
from scripts.generation_config_args import llama_args_from_config
from scripts.generation_config_args import load_llama_args


class GenerationConfigArgsTest(unittest.TestCase):
    def test_gemma4_config(self) -> None:
        args = llama_args_from_config(
            {
                "do_sample": True,
                "temperature": 1.0,
                "top_k": 64,
                "top_p": 0.95,
                "suppress_tokens": [258883, 258882],
            }
        )

        self.assertEqual(
            args,
            [
                "--temp",
                "1.0",
                "--top-k",
                "64",
                "--top-p",
                "0.95",
                "--logit-bias",
                "258883-inf",
                "--logit-bias",
                "258882-inf",
            ],
        )

    def test_do_sample_false_uses_greedy_decoding(self) -> None:
        args = llama_args_from_config(
            {"do_sample": False, "temperature": 1.2, "top_k": 50}
        )
        self.assertEqual(args[:2], ["--temp", "0"])
        self.assertEqual(args[2:], ["--top-k", "50"])

    def test_transformers_only_fields_are_ignored(self) -> None:
        self.assertEqual(
            llama_args_from_config(
                {
                    "bos_token_id": 2,
                    "eos_token_id": 1,
                    "cache_implementation": "hybrid",
                }
            ),
            [],
        )

    def test_invalid_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(GenerationConfigError, "top_p"):
            llama_args_from_config({"top_p": 1.5})

    def test_loads_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generation_config.json"
            path.write_text(json.dumps({"temperature": 0.7}), encoding="utf-8")
            self.assertEqual(load_llama_args(path), ["--temp", "0.7"])


if __name__ == "__main__":
    unittest.main()
