#!/usr/bin/env python3
"""
Web head dumper
---------------
Idea : give my intern routine a quick hit of "check this hosted site" without
reaching for a paid scanner. Reads a list of targets, sends a HEAD request to
each one, follows redirects, and drops one JSON file per target with the final
URL, status code, and response headers.

Handle things one at a time. If one target dies (bad DNS, timeout, 403, whatever),
the rest keep going -- no single failure should kill the batch.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: run `python -m pip install requests` first.", file=sys.stderr)
    sys.exit(2)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Head-request dumper for a list of URLs."
    )
    parser.add_argument(
        "targets",
        help="Text file with one URL per line (comments and blank lines are ignored).",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        default="dumps",
        help="Folder where per-target JSON files get written (default: dumps).",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=20,
        help="How many targets run at the same time (default: 20).",
    )
    parser.add_argument(
        "--no-redirects",
        action="store_true",
        help="Stop at the first response instead of following redirects.",
    )
    return parser.parse_args(argv)


def read_targets(path):
    targets = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        targets.append(line)
    return targets


def make_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "web-head-dumper/1.0"})
    return session


def dump_target(url, no_redirects, session, outdir):
    """One target: send the request, hold the result, write the JSON file."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    payload = {
        "requested_url": url,
        "final_url": None,
        "status": None,
        "headers": {},
        "error": None,
    }

    try:
        response = session.head(
            url,
            allow_redirects=not no_redirects,
            timeout=10,
            headers={"User-Agent": "web-head-dumper/1.0"},
        )
        payload["final_url"] = str(response.url)
        payload["status"] = response.status_code
        payload["headers"] = {k.lower(): v for k, v in response.headers.items()}
    except requests.RequestException as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"

    outdir.mkdir(parents=True, exist_ok=True)

    # Make the filename from the URL so it is readable, and unique enough.
    safe = "".join(c if c.isalnum() or c in ":/_-" else "_" for c in payload["requested_url"])
    safe = safe.replace("://", "__").replace("/", "_")
    dump_path = outdir / f"{safe}.json"
    dump_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload, dump_path


def main(argv=None):
    args = parse_args(argv)

    target_file = Path(args.targets)
    if not target_file.is_file():
        print(f"error: targets file not found: {target_file}", file=sys.stderr)
        sys.exit(1)

    targets = read_targets(target_file)
    if not targets:
        print("error: no targets found in file.", file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir)
    session = make_session()

    results = []
    started = time.monotonic()

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        future_to_url = {pool.submit(dump_target, url, args.no_redirects, session, outdir): url for url in targets}
        for future in as_completed(future_to_url):
            try:
                payload, dump_path = future.result()
            except Exception as exc:  # defensive: keep the batch alive
                payload, dump_path = None, None
                print(f"worker fault for {future_to_url[future]}: {exc}")
            if payload is not None:
                results.append(payload)
                print(
                    f"{payload['requested_url']}: status={payload['status']} "
                    f"err={payload['error'] or 'ok'}"
                )

    print(f"\nDone in {time.monotonic() - started:.2f}s | {len(targets)} targets | {len(results)} files in {outdir}")


if __name__ == "__main__":
    sys.exit(main())
