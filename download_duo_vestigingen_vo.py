#!/usr/bin/env python3
"""
Download DUO 'Alle vestigingen VO' CSV (school addresses with postcode by BRIN/VESTIGINGSCODE).
Saves to duo_vestigingen_vo.csv in the script directory.
"""

import urllib.request
from pathlib import Path

URL = "https://duo.nl/open_onderwijsdata/images/02.-alle-vestigingen-vo.csv"
OUTPUT = Path(__file__).resolve().parent / "duo_vestigingen_vo.csv"


def main():
    print(f"Downloading {URL} ...")
    urllib.request.urlretrieve(URL, OUTPUT)
    size = OUTPUT.stat().st_size
    print(f"Saved to {OUTPUT} ({size:,} bytes)")


if __name__ == "__main__":
    main()
