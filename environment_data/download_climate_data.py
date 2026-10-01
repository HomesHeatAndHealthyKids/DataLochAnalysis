#!/usr/bin/env python3
"""
HadUK-Grid downloader (token-ready) for authenticated CEDA access. There is a large amount of data to download 
so the download is kept separate from combining and filtering the data. This script is intended to be run from the command line.
Please get a CEDA access token from CEDA. Create a login to the CEDA archive (https://data.ceda.ac.uk/) and generate a token from your account settings. 
You can also use Basic auth via ~/.netrc or environment variables.

Features:
- Supports variables: tas, tasmin, tasmax, groundfrost, hurs, sfcWind, snowLying, sun, rainfall
- CEDA access token via --token/--token-file or CEDA_TOKEN env; falls back to Basic auth (.netrc/env/prompt) if no token
- Monthly cadence (mon), 1km grid, data release v20250415 (configurable via constants)
- Year filtering (default 2011–2024)
- Concurrent, resumable downloads with a single total progress bar
- Validates NetCDF content to avoid saving HTML login/licence pages
"""

import os
import re
import sys
import signal
import pathlib
import threading
import getpass
import netrc
import argparse
from urllib.parse import urljoin, urlparse

import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Dataset path components (adjust if needed)
DATASET_VERSION = "v1.3.1.ceda"
GRID = "1km"
FREQ = "mon"
DATA_RELEASE = "v20250415"
TOKEN = None


# Root and allowed variables
ROOT = "https://data.ceda.ac.uk/badc/ukmo-hadobs/data/insitu/MOHC/HadOBS/HadUK-Grid"
ALLOWED_VARS = [
    "tas", "tasmin", "tasmax", "groundfrost", "hurs", "sfcWind", "snowLying", "sun", "rainfall"
]

# Defaults
DEFAULT_START_YEAR = 2011
DEFAULT_END_YEAR = 2024
DEFAULT_OUT_BASE = "haduk_grid_downloads"

# Networking parameters
MAX_WORKERS_DEFAULT = 3   # be gentle to the archive
CHUNK_SIZE = 1 << 20      # 1 MiB
TIMEOUT = (10, 90)        # (connect, read)
HEADERS = {"User-Agent": "python-requests (HadUK-Grid 1km mon downloader)"}

# Thread-safe progress bar
tqdm_lock = threading.Lock()
total_pbar = None


def build_base_url(variable: str) -> str:
    return "/".join([
        ROOT,
        DATASET_VERSION,
        GRID,
        variable,
        FREQ,
        DATA_RELEASE,
        ""
    ])


def ensure_dir(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def load_token(args):
    """
    if --token is provided, use it; else if --token-file is provided, read it; else if CEDA_TOKEN env var is set, use it.
    """
    if args.token:
        return args.token
    if args.token_file:
        with open(args.token_file, "r") as f:
            return f.read().strip()
    if os.getenv("CEDA_TOKEN"):
        return os.getenv("CEDA_TOKEN")
    return TOKEN

def load_credentials():
    """
    Fallback Basic auth if no token:
      - Environment variables: CEDA_USERNAME, CEDA_PASSWORD
      - ~/.netrc or _netrc (machine data.ceda.ac.uk)
      - Interactive prompt (if tty)
    """
    user = os.getenv("CEDA_USERNAME") or os.getenv("CEDA_USER")
    pwd  = os.getenv("CEDA_PASSWORD") or os.getenv("CEDA_PASS")
    if user and pwd:
        return user, pwd

    try:
        n = netrc.netrc()
        for host in ["data.ceda.ac.uk", "ceda.ac.uk"]:
            auth = n.authenticators(host)
            if auth:
                login = auth[0]
                password = auth[2]
                if login and password:
                    return login, password
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Warning: could not parse netrc: {e}", file=sys.stderr)

    if sys.stdin.isatty():
        print("CEDA credentials are required (consider using ~/.netrc or env vars).")
        user = input("CEDA username: ").strip()
        pwd = getpass.getpass("CEDA password: ")
        if user and pwd:
            return user, pwd

    return None, None


def build_session(token=None, auth=None, max_workers=MAX_WORKERS_DEFAULT):
    session = requests.Session()
    session.headers.update(HEADERS)
    session.trust_env = True  # allow proxies/CA bundles from env

    # Retries for transient errors
    retry = Retry(
        total=5,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["HEAD", "GET"])
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=max_workers, pool_maxsize=max_workers)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    if token:
        # Add Bearer token to all requests
        session.headers["Authorization"] = f"Bearer {token}"
    elif auth:
        session.auth = HTTPBasicAuth(*auth)
    return session


def require_auth_or_exit(resp, using_token=False):
    if resp.status_code in (401, 403):
        msg = "Authentication failed or access not permitted."
        if using_token:
            msg += " Check that your CEDA token is valid, not expired, and that you have accepted the dataset licence."
        else:
            msg += " Check credentials and that you have accepted the dataset licence."
        print(msg, file=sys.stderr)
        sys.exit(1)


def list_nc_files(session, base_url, using_token=False):
    """Scrape directory listing and return absolute URLs for .nc files."""
    r = session.get(base_url, timeout=TIMEOUT, allow_redirects=True)
    if r.status_code in (401, 403):
        require_auth_or_exit(r, using_token)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    urls = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href or href in ("../", "/"):
            continue
        if href.lower().endswith(".nc") or ".nc?" in href.lower():
            urls.append(urljoin(base_url, href))
    return urls


def filename_from_url(url):
    return os.path.basename(urlparse(url).path)


def extract_years_from_name(name):
    years = set()
    for y in re.findall(r'(?<!\d)(\d{4})(?!\d)', name):
        years.add(int(y))
    for y6 in re.findall(r'(?<!\d)(\d{6})(?!\d)', name):
        years.add(int(y6[:4]))
    for a, b in re.findall(r'(\d{4,6})-(\d{4,6})', name):
        years.add(int(a[:4] if len(a) == 6 else a))
        years.add(int(b[:4] if len(b) == 6 else b))
    return years


def filter_urls_by_year(urls, year_start, year_end):
    want = set(range(year_start, year_end + 1))
    out = []
    for u in urls:
        fn = filename_from_url(u)
        yrs = extract_years_from_name(fn)
        if yrs & want:
            out.append(u)
    return sorted(out)


def head_content_info(session, url, using_token=False):
    """Return (size_bytes or None, accept_ranges_bool)."""
    try:
        resp = session.head(url, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code in (401, 403):
            require_auth_or_exit(resp, using_token)
        if resp.status_code >= 400:
            # Fallback: tiny ranged GET to fetch headers
            resp = session.get(url, headers={"Range": "bytes=0-0"}, stream=True, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code in (401, 403):
                require_auth_or_exit(resp, using_token)

        size = None
        if "Content-Range" in resp.headers and "/" in resp.headers["Content-Range"]:
            try:
                size = int(resp.headers["Content-Range"].split("/")[-1])
            except Exception:
                size = None
        elif "Content-Length" in resp.headers:
            try:
                size = int(resp.headers.get("Content-Length"))
            except Exception:
                size = None

        accept_ranges = resp.headers.get("Accept-Ranges", "").lower() == "bytes"
        return size, accept_ranges
    except requests.RequestException:
        return None, False


def download_one(session, url, out_dir, pbar, using_token=False):
    fn = filename_from_url(url)
    dest = os.path.join(out_dir, fn)

    remote_size, accept_ranges = head_content_info(session, url, using_token=using_token)
    local_size = os.path.getsize(dest) if os.path.exists(dest) else 0

    if remote_size is not None and local_size == remote_size and remote_size > 0:
        return fn, "skipped (already complete)"

    headers = {}
    mode = "wb"
    if accept_ranges and os.path.exists(dest) and local_size > 0 and (remote_size is None or local_size < remote_size):
        headers["Range"] = f"bytes={local_size}-"
        mode = "ab"

    try:
        # First request; allow redirects but validate destination/content
        with session.get(url, headers=headers, stream=True, timeout=TIMEOUT, allow_redirects=True) as r:
            if r.status_code in (401, 403):
                require_auth_or_exit(r, using_token)
            r.raise_for_status()

            # Check Content-Type and magic bytes to avoid writing HTML
            ct = (r.headers.get("Content-Type") or "").lower()
            looks_like_netcdf_ct = ("netcdf" in ct) or ("application/octet-stream" in ct)

            # Peek first chunk
            data_iter = r.iter_content(chunk_size=65536)
            first_chunk = b""
            for chunk in data_iter:
                if chunk:
                    first_chunk = chunk
                    break

            def has_netcdf_magic(buf: bytes) -> bool:
                return (
                    buf.startswith(b"CDF\x01") or  # netCDF classic
                    buf.startswith(b"CDF\x02") or
                    buf.startswith(b"\x89HDF\r\n\x1a\n")  # netCDF-4/HDF5
                )

            if not looks_like_netcdf_ct and not has_netcdf_magic(first_chunk):
                # Likely HTML login/licence page or proxy message
                snippet = first_chunk[:400].decode("utf-8", errors="replace").replace("\n", " ")
                hint = "Unexpected content (ct={}). Possible causes: token invalid/expired, licence not accepted, or proxy/captive portal.".format(ct or "unknown")
                return fn, f"{hint} Snippet: {snippet!r}"

            # If server ignored Range, restart clean
            if "Range" in headers and (r.status_code == 200):
                mode = "wb"

            with open(dest, mode) as f:
                if first_chunk:
                    f.write(first_chunk)
                    with tqdm_lock:
                        pbar.update(len(first_chunk))
                for chunk in data_iter:
                    if not chunk:
                        continue
                    f.write(chunk)
                    with tqdm_lock:
                        pbar.update(len(chunk))

        if remote_size is not None and os.path.getsize(dest) != remote_size:
            return fn, "warning: size mismatch"
        return fn, "downloaded"
    except requests.RequestException as e:
        return fn, f"error: {e}"
    except Exception as e:
        return fn, f"error: {e}"


def graceful_exit(signum, frame):
    print("\nReceived interrupt, exiting...", file=sys.stderr)
    try:
        if total_pbar is not None:
            total_pbar.close()
    finally:
        sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(description="Download HadUK-Grid monthly 1km NetCDF files (CEDA token-ready).")
    p.add_argument("--vars", nargs="+", default=["tas"],
                   help=f"Variables to download (space-separated). Allowed: {', '.join(ALLOWED_VARS)}. Default: tas")
    p.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR, help="Start year (inclusive).")
    p.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR, help="End year (inclusive).")
    p.add_argument("--outdir", default=DEFAULT_OUT_BASE, help="Base output directory.")
    p.add_argument("--max-workers", type=int, default=MAX_WORKERS_DEFAULT, help="Parallel downloads (be gentle).")
    # Token options
    p.add_argument("--token", default=None, help="CEDA access token string.")
    p.add_argument("--token-file", default=None, help="Path to a file containing the CEDA access token.")
    return p.parse_args()


def main():
    signal.signal(signal.SIGINT, graceful_exit)
    args = parse_args()

    # Validate variables
    variables = []
    for v in args.vars:
        if v not in ALLOWED_VARS:
            print(f"Error: variable '{v}' is not supported. Choose from: {', '.join(ALLOWED_VARS)}", file=sys.stderr)
            sys.exit(2)
        variables.append(v)

    if args.start_year > args.end_year:
        print("Error: start-year must be <= end-year.", file=sys.stderr)
        sys.exit(2)

    # Prepare output structure
    ensure_dir(args.outdir)
    var_outdirs = {v: os.path.join(args.outdir, v) for v in variables}
    for d in var_outdirs.values():
        ensure_dir(d)

    # Auth preference: token > basic
    token = load_token(args)
    user = pwd = None
    if not token:
        user, pwd = load_credentials()
        if not user or not pwd:
            print(
                "No CEDA token or credentials available.\n"
                "- Preferred: set CEDA_TOKEN env var, --token, or --token-file\n"
                "- Fallback: create ~/.netrc with:\n"
                "    machine data.ceda.ac.uk\n"
                "      login YOUR_CEDA_USERNAME\n"
                "      password YOUR_CEDA_PASSWORD\n"
                "  (chmod 600 ~/.netrc)\n",
                file=sys.stderr,
            )
            sys.exit(1)

    with build_session(token=token, auth=(user, pwd) if (user and pwd and not token) else None,
                       max_workers=args.max_workers) as session:
        using_token = bool(token)

        # Collect all URLs across variables
        all_target_pairs = []  # list of (url, outdir)
        for v in variables:
            base_url = build_base_url(v)
            print(f"Listing directory for {v} ...")
            try:
                all_urls = list_nc_files(session, base_url, using_token=using_token)
            except requests.HTTPError as e:
                print(f"HTTP error fetching directory for {v}: {e}", file=sys.stderr)
                sys.exit(1)
            if not all_urls:
                print(f"No .nc files found for {v} (check access/URL).", file=sys.stderr)
                continue

            urls = filter_urls_by_year(all_urls, args.start_year, args.end_year)
            if not urls:
                print(f"No .nc files matched {args.start_year}-{args.end_year} for {v}.")
                continue

            print(f"  {v}: {len(urls)} .nc files in {args.start_year}-{args.end_year}")
            for u in urls:
                all_target_pairs.append((u, var_outdirs[v]))

        if not all_target_pairs:
            print("No files to download. Exiting.")
            sys.exit(0)

        # Compute total size for unified progress bar
        print("Querying sizes...")
        total_bytes = 0
        for u, _od in all_target_pairs:
            sz, _ = head_content_info(session, u, using_token=using_token)
            if isinstance(sz, int) and sz >= 0:
                total_bytes += sz

        global total_pbar
        total_pbar = tqdm(
            total=total_bytes if total_bytes > 0 else None,
            unit="B", unit_scale=True, unit_divisor=1024,
            desc="Total", leave=True
        )

        # Download
        results = []
        with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            futures = [ex.submit(download_one, session, u, od, total_pbar, using_token) for (u, od) in all_target_pairs]
            for fut in as_completed(futures):
                results.append(fut.result())

        total_pbar.close()

        # Summary
        status_counts = {}
        for fn, status in results:
            status_counts[status] = status_counts.get(status, 0) + 1

        print("Summary:")
        for status, count in sorted(status_counts.items(), key=lambda x: x[0]):
            print(f"  {status}: {count}")
        print(f"Files saved under: {os.path.abspath(args.outdir)}")
        for v in variables:
            print(f"  - {v}: {os.path.abspath(var_outdirs[v])}")


if __name__ == "__main__":
    # pip install requests beautifulsoup4 tqdm
    main()
