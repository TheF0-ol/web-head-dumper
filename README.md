# Web Head Dumper

Utility to quickly check a list of hosted URLs. Reads a text file with one URL
per line, sends a HEAD request to each, follows redirects, and saves one JSON
file per target with the final URL, status code, and response headers.

## Why

Quick way to check whether a host is online and what it returns, without reaching
for a paid scanner. Useful for internship reporting and light URL verification.

## Requirements

- Python 3.9+
- `requests` (only dependency)

Install:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python web_head_dumper.py targets.txt -o dumps -t 20
```

- `targets.txt` — one URL per line (comments with `#` and blank lines are ignored).
- `-o dumps` — folder where per-target JSON files are written (default: `dumps`).
- `-t 20` — how many targets run at the same time (default: 20).

Each dump file looks like:

```json
{
  "requested_url": "https://example.com",
  "final_url": "https://example.com/",
  "status": 200,
  "headers": { "server": "cloudflare", "content-type": "text/html" },
  "error": null
}
```

## Notes

- Bad targets do not stop the batch. One unreachable URL only shows up in that
  dump's `error` field.
- `--no-redirects` stops at the first response instead of following redirects.

## Scope

This is a utility for light URL verification and internship reporting. It is not
a security scanner. Only run it against hosts you own or have permission to check.
