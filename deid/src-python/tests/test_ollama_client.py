from __future__ import annotations

import json
import unittest

from ollama_client import OllamaClient


class _FakeResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def __iter__(self):
        return iter(self._lines)

    def read(self) -> bytes:
        return b"\n".join(self._lines)


class OllamaClientTests(unittest.TestCase):
    def test_build_user_content_contains_target_instruction_and_context(self) -> None:
        content = OllamaClient.build_user_content(
            instruction="Switch David with Bruce",
            target="input",
            current_text="David went home.",
            other_text="Bruce stayed out.",
        )
        self.assertIn("TARGET: input", content)
        self.assertIn("Switch David with Bruce", content)
        self.assertIn("CURRENT_TEXT:", content)
        self.assertIn("OTHER_TEXT:", content)

    def test_stream_chat_emits_tokens_and_sends_fixed_options(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["timeout"] = timeout
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse(
                [
                    json.dumps({"message": {"content": "Hello "}, "done": False}).encode("utf-8"),
                    json.dumps({"message": {"content": "world"}, "done": False}).encode("utf-8"),
                    json.dumps({"done": True}).encode("utf-8"),
                ]
            )

        client = OllamaClient(
            endpoint="http://127.0.0.1:11434",
            model="llama3.1:8b",
            urlopen_fn=fake_urlopen,
        )
        tokens = list(
            client.stream_chat(
                instruction="Switch David with Bruce",
                target="input",
                current_text="David met Anne.",
                other_text="Output placeholder.",
                history=[{"role": "user", "content": "Earlier instruction"}],
            )
        )
        self.assertEqual(tokens, ["Hello ", "world"])
        self.assertEqual(captured["url"], "http://127.0.0.1:11434/api/chat")
        payload = captured["payload"]
        self.assertIsInstance(payload, dict)
        payload_dict = payload if isinstance(payload, dict) else {}
        self.assertEqual(payload_dict["model"], "llama3.1:8b")
        self.assertTrue(payload_dict["stream"])
        self.assertFalse(payload_dict["think"])
        options = payload_dict["options"]
        self.assertEqual(options["temperature"], 0.4)
        self.assertEqual(options["top_p"], 0.9)
        self.assertEqual(options["seed"], 420)
        messages = payload_dict["messages"]
        self.assertGreaterEqual(len(messages), 3)
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("Earlier instruction", messages[1]["content"])
        self.assertIn("CURRENT_TEXT:", messages[-1]["content"])

    def test_list_models_reads_tags_payload(self) -> None:
        def fake_urlopen(_req, timeout=None):
            body = json.dumps(
                {"models": [{"name": "qwen3.5:9b"}, {"name": "gemma3:270m-it-qat"}]}
            ).encode("utf-8")
            return _FakeResponse([body])

        client = OllamaClient(
            endpoint="http://127.0.0.1:11434",
            model="qwen3.5:9b",
            urlopen_fn=fake_urlopen,
        )
        self.assertEqual(client.list_models(), ["qwen3.5:9b", "gemma3:270m-it-qat"])


if __name__ == "__main__":
    unittest.main()
