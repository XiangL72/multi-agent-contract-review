"""Run a text/TXT review. Choose --mock or --real explicitly."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .pipeline.runner import ReviewInputError, decode_txt, run_review
from .pipeline.state import ReviewStatus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--file", type=Path, help="UTF-8 TXT only")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="Synthetic control-flow demo; no provider request")
    mode.add_argument("--real", action="store_true", help="Use configured paid provider")
    parser.add_argument("--output", type=Path, help="Write JSON result to this path")
    parser.add_argument("--max-calls", type=int, choices=range(1, 9), default=8,
                        help="Per-run provider request cap, at most 8")
    args = parser.parse_args()
    if args.mock:
        from .demo.fake_llm import install_demo_model
        install_demo_model()
    try:
        if args.file is not None:
            if args.file.suffix.lower() != ".txt":
                raise ReviewInputError("UNSUPPORTED_FORMAT", "Only TXT files are supported")
            text = decode_txt(args.file.read_bytes())
        else:
            text = args.text
        state = asyncio.run(run_review(text, max_calls=args.max_calls))
        data = {"mock": bool(args.mock), "result": state.model_dump(mode="json")}
        code = {ReviewStatus.SUCCESS: 0, ReviewStatus.PARTIAL: 2,
                ReviewStatus.TIMED_OUT: 124}.get(state.status, 1)
    except ReviewInputError as exc:
        data = {"mock": bool(args.mock), "error": {"code": getattr(exc, "code", "INPUT_ERROR"),
                                                   "message": str(exc)}}
        code = 1
    except OSError:
        data = {"mock": bool(args.mock), "error": {"code": "INPUT_IO_ERROR", "message": "Cannot read the input file."}}
        code = 1
    rendered = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
