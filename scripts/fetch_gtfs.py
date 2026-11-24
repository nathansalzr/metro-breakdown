"""Download LA Metro's rail schedule (GTFS) to data/raw/gtfs_rail.zip.

Usage:
    python scripts/fetch_gtfs.py              # LA Metro rail (default)
    python scripts/fetch_gtfs.py --url URL    # any other agency's GTFS zip

Source: LA Metro publishes its rail schedule at https://gitlab.com/LACMTA/gtfs_rail
(overview: https://developer.metro.net/). The download is ~1.6 MB and is not committed
to git (data/raw/ is in .gitignore); anyone can re-download it with this script.
"""

import argparse
import sys
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://gitlab.com/LACMTA/gtfs_rail/-/raw/master/gtfs_rail.zip"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "gtfs_rail.zip"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a GTFS feed.")
    parser.add_argument("--url", default=DEFAULT_URL, help="GTFS zip to download")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where to save it")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {args.url}")
    with urllib.request.urlopen(args.url, timeout=60) as response:
        data = response.read()
    args.out.write_bytes(data)
    print(f"Saved {args.out} ({len(data) / 1e6:.1f} MB)")
    print("Next: python scripts/inspect_network.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
