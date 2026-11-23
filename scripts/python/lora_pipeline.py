# -*- coding: utf-8 -*-
"""LoRA training pipeline placeholder — documents the intended flow."""
from __future__ import annotations

MESSAGE = """
GGUF Runner — LoRA pipeline (stub)

Intended steps (run manually with your own GPU stack):
  1. Collect chat logs / dataset under dataset/
  2. Convert to Alpaca or ShareGPT JSONL
  3. Fine-tune with unsloth / axolotl / llama-factory on a base model
  4. Merge LoRA and export GGUF (llama.cpp convert + quantize)
  5. Place the resulting .gguf into models/

See docs/LORA_PIPELINE.md and docs/LORA_TO_GGUF.md for details.

This stub does not train models offline by default (too heavy for the portable bundle).
"""


def main() -> int:
    print(MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
