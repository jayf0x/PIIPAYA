from __future__ import annotations

import unittest

from processing import chunk_text


class ProcessingTests(unittest.TestCase):
    def test_chunk_text_preserves_double_newline_boundaries(self) -> None:
        text = "First paragraph.\n\nSecond paragraph."
        chunks = chunk_text(text, chunk_size_chars=20)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertIn("\n\n", "".join(chunks))
        self.assertEqual("".join(chunks), text)

    def test_chunk_text_splits_oversized_piece(self) -> None:
        text = "A" * 5000
        chunks = chunk_text(text, chunk_size_chars=1000)
        self.assertTrue(all(len(chunk) <= 1000 for chunk in chunks))
        self.assertEqual("".join(chunks), text)

    def test_chunk_text_empty_input(self) -> None:
        self.assertEqual(chunk_text("", 1000), [""])


if __name__ == "__main__":
    unittest.main()
