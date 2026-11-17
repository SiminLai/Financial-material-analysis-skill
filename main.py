import argparse
import asyncio
import contextlib
import json
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Evidence-first financial research")
    parser.add_argument("--input-file", default=os.getenv("INPUT_FILE"), required=not bool(os.getenv("INPUT_FILE")))
    parser.add_argument("--run-id", "--thread-id", dest="run_id")
    parser.add_argument("--output-dir", default="workspace/runs")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "deepseek-chat"))
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--enable-external-search", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    with contextlib.redirect_stdout(sys.stderr):
        from runtime.runtime import analyze_document
        result = asyncio.run(analyze_document(
            args.input_file, output_dir=args.output_dir, run_id=args.run_id,
            model=args.model, demo=args.demo,
            allow_external_search=args.enable_external_search,
        ))
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return {"succeeded": 0, "needs_review": 2, "failed": 1}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
