import os
import re
import time
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://moses.creighton.edu/kripke/jesuitrelations/"  # TOC page 

# Polite delay between requests (seconds)
SLEEP = 0.5

def safe_filename(url: str) -> str:
    """Convert a URL path to a safe local filename."""
    path = urlparse(url).path
    name = os.path.basename(path) or "index.html"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name

def fetch(session: requests.Session, url: str) -> bytes:
    r = session.get(url, timeout=60)
    r.raise_for_status()
    return r.content

def main(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "JesuitRelationsFreeze/1.0 (scholarly download; contact: you@example.edu)"
    })

    # 1) Download index page
    index_bytes = fetch(session, INDEX_URL)
    index_path = os.path.join(out_dir, "index.html")
    with open(index_path, "wb") as f:
        f.write(index_bytes)

    # 2) Parse volume links from index
    soup = BeautifulSoup(index_bytes, "lxml")

    # Common pattern on this site: relations_XX.html (and sometimes relations_03.html etc.)
    rel_pat = re.compile(r"relations[_-]?\d+\.html$", re.IGNORECASE)

    volume_urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        full_url = urljoin(INDEX_URL, href)
        if rel_pat.search(full_url):
            volume_urls.append(full_url)

    # De-duplicate while preserving order
    seen = set()
    volume_urls = [u for u in volume_urls if not (u in seen or seen.add(u))]

    if not volume_urls:
        print("ERROR: Did not find any volume links matching relations_XX.html on the index page.")
        print("The site layout may have changed; inspect index.html and adjust the link pattern.")
        sys.exit(1)

    # 3) Download each volume HTML
    for i, url in enumerate(volume_urls, start=1):
        time.sleep(SLEEP)
        b = fetch(session, url)
        fn = safe_filename(url)
        out_path = os.path.join(out_dir, fn)
        with open(out_path, "wb") as f:
            f.write(b)
        print(f"[{i}/{len(volume_urls)}] saved {fn}")

    # 4) Sanity check: do we have 71?
    # (You asked for 71; this prints what was found on the index page.)
    print("\nDone.")
    print(f"Index saved as: {index_path}")
    print(f"Volume files downloaded: {len(volume_urls)}")
    print(f"Output directory: {os.path.abspath(out_dir)}")

if __name__ == "__main__":
    # Usage: python download_jesuit_relations.py jesuit_relations_html
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "jesuit_relations_html"
    main(out_dir)
