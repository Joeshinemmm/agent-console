"""Synthetic external JSONL producer. Does not import agent-console or ai-agent."""

import argparse
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()
    with args.path.open("rb") as stream:
        for line in stream:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
            time.sleep(max(0, args.delay))


if __name__ == "__main__":
    main()
