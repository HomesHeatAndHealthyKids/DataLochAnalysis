""" 
Download and combine UK DEFRA PCM pollution data for UK (2011–2024)

Most of the code is scraping the website to find the links to the CSV files, downloading them, extracting them if they are zipped, 
and then combining them into a single CSV file. After combining, it filters the data to only include records from Scotland (actually latitude > 55).

"""
import re
import io
import os
import sys
import time
import json
import shutil
import zipfile
import logging
import random
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import geopandas as gpd
from shapely.geometry import Point

# ----------------------------
# Configuration
# ----------------------------
BASE_URL = "https://uk-air.defra.gov.uk/data/pcm-data"
OUTPUT_DIR = Path("defra_pcm_downloads")
RAW_DIR = OUTPUT_DIR / "raw"
EXTRACT_DIR = OUTPUT_DIR / "extracted"
MANIFEST_PATH = OUTPUT_DIR / "manifest.jsonl"

YEARS = list(range(2011, 2025))  # inclusive 2011–2024
# Canonical pollutant labels and patterns to match in link text or filename
# --- Robust pollutant matching (treat _ and - as boundaries) ---
BOUND = r"(?<![A-Za-z0-9])"   # left boundary: not a letter/number
ENDB = r"(?![A-Za-z0-9])"     # right boundary: not a letter/number

POLLUTANT_REGEX = {
    "PM10": [
        re.compile(BOUND + r"pm10" + ENDB, re.I),
        re.compile(r"particulate[\s\-_]?matter[\s\-_]?\(?10\)?", re.I),
    ],
    "PM2.5": [
        re.compile(BOUND + r"pm2[\.\-_/]?5" + ENDB, re.I),
        re.compile(BOUND + r"pm25" + ENDB, re.I),
        re.compile(r"particulate[\s\-_]?matter[\s\-_]?\(?2\.?5\)?", re.I),
    ],
    "Benzene": [
        re.compile(BOUND + r"benzene" + ENDB, re.I),
        re.compile(BOUND + r"c6h6" + ENDB, re.I),
    ],
    "SO2": [
        re.compile(BOUND + r"so2" + ENDB, re.I),
        re.compile(r"sulphur[\s\-_]?dioxide", re.I),
        re.compile(r"sulfur[\s\-_]?dioxide", re.I),
    ],
    "NO2": [
        re.compile(BOUND + r"no2" + ENDB, re.I),
        re.compile(r"nitrogen[\s\-_]?dioxide", re.I),
    ],
    "NOx": [
        re.compile(BOUND + r"nox" + ENDB, re.I),
        re.compile(r"nitrogen[\s\-_]?oxides?", re.I),
    ],
    "CO": [
        re.compile(BOUND + r"co" + ENDB, re.I),       # short token
        re.compile(r"carbon[\s\-_]?monoxide", re.I),   # spelled-out
    ],
    "Ozone": [
        re.compile(BOUND + r"o3" + ENDB, re.I),
        re.compile(r"ozone", re.I),
    ],
}




# Only consider these filetypes
ALLOWED_EXTS = (".csv", ".zip")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)


# ----------------------------
# HTTP session with retry
# ----------------------------
def make_session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; pcm-scraper/1.0; +https://example.org)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return s


# ----------------------------
# Utilities
# ----------------------------
def slugify(s: str) -> str:
    s = unquote(s)
    s = re.sub(r"[^\w\-.]+", "_", s.strip(), flags=re.UNICODE)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")

def guess_filename_from_cd(resp, default: str) -> str:
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^\";]+)"?', cd, flags=re.I)
    if m:
        return slugify(m.group(1))
    return default

def ensure_dirs():
    for p in [OUTPUT_DIR, RAW_DIR, EXTRACT_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def is_allowed(href: str) -> bool:
    if not href:
        return False
    href = href.lower()
    return any(href.endswith(ext) for ext in ALLOWED_EXTS) or ".csv" in href or ".zip" in href




def unique_stable_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]





def extract_if_zip(path: Path, dest_dir: Path) -> list[Path]:
    if path.suffix.lower() != ".zip":
        return []
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(path, "r") as zf:
        for member in zf.infolist():
            # Only extract CSV from the zip
            if not member.filename.lower().endswith(".csv"):
                continue
            # Sanitize filename
            safe_name = slugify(os.path.basename(member.filename))
            out_path = dest_dir / safe_name
            if not out_path.exists() or out_path.stat().st_size == 0:
                with zf.open(member, "r") as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            extracted.append(out_path)
    return extracted

# ----------------------------
# Manifest helpers
# ----------------------------
def write_manifest_record(rec: dict):
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def load_manifest():
    if not MANIFEST_PATH.exists():
        return []
    out = []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

# Canonicalization helper

def _canon_pol(s: str) -> str | None:
    s = (s or "").lower()
    s = s.replace("pm2.5", "pm25").replace(" ", "").replace("_", "").replace("-", "")
    if s == "pm10":
        return "PM10"
    if s in ("pm25",):
        return "PM2.5"
    if s in ("no2", "nitrogendioxide"):
        return "NO2"
    if s in ("nox", "nitrogenoxides", "nitrogenoxide"):
        return "NOx"
    if s in ("so2", "sulphurdioxide", "sulfurdioxide"):
        return "SO2"
    if s in ("o3", "ozone", "dgt120", "somo35", "som35", "aot40", "mda8", "w126"):
        return "Ozone"
    if s in ("benzene", "c6h6", "bz"):
        return "Benzene"
    if s in ("co", "carbonmonoxide"):
        return "CO"
    return None

# map<token>... where token is a pollutant short code (now includes "bz")
MAP_PREFIX_RE = re.compile(
    r"map[_-]?(pm10|pm2[\.\-_/]?5|pm25|no2|nox|so2|o3|co|benzene|bz|dgt120|somo35|som35|aot40|mda8|w126)",
    re.I,
)
# Ozone metric hints (files that don't include o3/ozone but are ozone by metric)
# Examples: mapdgt120_12.csv, mapasomo35_2019.zip, mapaot40_2018.csv, mda8
OZONE_HINT_RE = re.compile(r"(dgt120|somo35|som35|aot40|mda8|w126)", re.I)

GENERIC_POL_RE = re.compile(
    r"(pm10|pm2[\.\-_/]?5|pm25|no2|nox|so2|o3|ozone|benzene|carbon[\s\-_]?monoxide|"
    r"nitrogen[\s\-_]?dioxide|nitrogen[\s\-_]?oxides?)",
    re.I,
)

def infer_pollutant(text_or_url: str) -> str | None:
    if not text_or_url:
        return None
    s = text_or_url.lower()

    # Use basename first
    try:
        base = os.path.basename(urlparse(s).path)
    except Exception:
        base = s
    name = os.path.splitext(base)[0]

    # 1) map<token> shortcut
    m = MAP_PREFIX_RE.search(name)
    if m:
        return _canon_pol(m.group(1))

    # 2) Ozone metric hints (applies to many ozone layers without explicit o3/ozone)
    if OZONE_HINT_RE.search(name):
        return "Ozone"

    # 3) Fallback to generic phrases anywhere
    # Don't do this because it adds in local authority files and other
  #  m = GENERIC_POL_RE.search(s)
  #  if m:
  #      return _canon_pol(m.group(1))

    return None


def link_context_text(a_tag):
    parts = []
    # link text and title
    parts.append(a_tag.get_text(" ") or "")
    if a_tag.has_attr("title"):
        parts.append(a_tag["title"])
    # href
    href = a_tag.get("href", "")
    parts.append(href)

    # nearest useful ancestors for context
    for anc in a_tag.parents:
        if getattr(anc, "name", None) in ("li", "p", "td", "th", "tr", "div", "section"):
            parts.append(" ".join(anc.stripped_strings))
            # stop early at list item or table row
            if anc.name in ("li", "tr"):
                break
    return " ".join(filter(None, parts))

YEAR4_RE = re.compile(r"(20(?:1[1-9]|2[0-4]))", re.I)

# map<pol><YY>... pattern (covers mapso213ann, mapno214ann, etc.)
# Note: includes all target pollutants and aliases
MAPPOL_2DIGIT_RE = re.compile(
    r"map(?:pm10|pm2[\.\-_/]?5|pm25|no2|nox|so2|o3|co|benzene|bz)"
    r"(\d{2})(?:[^0-9]|$)",
    re.I,
)

def find_year(text_or_url: str):
    if not text_or_url:
        return None
    s = str(text_or_url)

    # 1) Prefer 4-digit year anywhere
    m = YEAR4_RE.search(s)
    if m:
        return int(m.group(1))

    # Work on basename without extension for 2-digit patterns
    try:
        base = os.path.basename(urlparse(s).path)
    except Exception:
        base = s
    name = os.path.splitext(base)[0].lower()

    # 2) map<pol><YY>(...) e.g., mapso213ann → 2013

    m = MAPPOL_2DIGIT_RE.search(name)
    if m:
        yy = int(m.group(1))
        if 11 <= yy <= 24:
            return 2000 + yy

    # 3) Generic 2-digit suffix with a separator (avoids catching “120” in dgt120)
    m2 = re.search(r"[_\-\s\.](\d{2})(?!\d)", name)
    if m2:
        yy = int(m2.group(1))
        if 11 <= yy <= 24:
            return 2000 + yy

    return None

def match_pollutant(text: str):
    t = text.lower()
    for pol, regs in POLLUTANT_REGEX.items():
        for rgx in regs:
            if rgx.search(t):
                return pol
    return None
# ----------------------------
# Scrape links
# ----------------------------
def scrape_links(session, url: str):
    logging.info(f"Fetching index page: {url}")
    r = session.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not is_allowed(href):
            continue
        abs_url = urljoin(url, href)

        parts = [a.get_text(" ") or "", a.get("title") or "", abs_url]
        anc = a.find_parent(["li", "tr", "p", "div", "td", "th"])
        if anc is not None:
            parts.append(" ".join(anc.stripped_strings))
        ctx = " ".join(p for p in parts if p).lower()

        pollutant = infer_pollutant(abs_url) or infer_pollutant(ctx)
        year = find_year(abs_url) or find_year(ctx)

        links.append(
            {
                "text": a.get_text(" ").strip(),
                "href": abs_url,
                "year": year,
                "pollutant": pollutant,
                "ext": os.path.splitext(urlparse(abs_url).path)[1].lower(),
                "context": ctx[:300],
            }
        )
    logging.info(f"Found {len(links)} candidate file links.")
    return links


def filter_links(links):
    desired_years = set(YEARS)
    desired_pols = {"PM10", "PM2.5", "Benzene", "SO2", "NO2", "NOx", "CO", "Ozone"}

    filtered = []
    for rec in links:
        if rec["ext"] not in ALLOWED_EXTS:
            continue

        # Try a final inference pass from URL if missing
        if rec.get("pollutant") is None:
            rec["pollutant"] = infer_pollutant(rec["href"]) or infer_pollutant(rec.get("context", ""))
        if rec.get("year") is None:
            rec["year"] = find_year(rec["href"]) or find_year(rec.get("context", ""))

        if rec["pollutant"] not in desired_pols:
            continue
        if rec["year"] not in desired_years:
            continue

        filtered.append(rec)

    # De-duplicate by URL
    seen = set()
    deduped = []
    for rec in filtered:
        if rec["href"] in seen:
            continue
        seen.add(rec["href"])
        deduped.append(rec)
    logging.info(f"Filtered to {len(deduped)} file links for target pollutants and years.")
    return deduped

def get_links():
    ensure_dirs()
    session = make_session()
    all_links = scrape_links(session, BASE_URL)
    links = filter_links(all_links)

    # Build a lookup to avoid re-downloading
    existing_manifest = load_manifest()
    seen_urls = {m["source_url"] for m in existing_manifest}
    for rec in links:
        logging.info(f'{rec['pollutant']} - {rec['year']} found')
    return links, seen_urls


# ----------------------------
# Download and extract
# ----------------------------
def download_file(session: requests.Session, url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Try to create a reasonable filename
    parsed = urlparse(url)
    base_name = os.path.basename(parsed.path)
    if not base_name:
        base_name = unique_stable_id(url) + ".dat"
    base_name = slugify(base_name)
    tmp_path = dest_dir / (base_name + ".part")
    final_path = dest_dir / base_name

    if final_path.exists() and final_path.stat().st_size > 0:
        return final_path

    with session.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        # Use Content-Disposition if present
        cand_name = guess_filename_from_cd(r, base_name)
        final_path = dest_dir / slugify(cand_name)
        tmp_path = dest_dir / (final_path.name + ".part")

        total = int(r.headers.get("Content-Length", 0)) or None
        with open(tmp_path, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=f"Downloading {final_path.name}"
        ) as pbar:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

    os.replace(tmp_path, final_path)
    # polite delay
    time.sleep(0.5 + random.random() * 0.5)
    return final_path

def download_csvs(links, seen_urls):
    session = make_session()
    for rec in links:
        url = rec["href"]
        pol = rec["pollutant"]
        yr = rec["year"]

        if url in seen_urls:
            logging.info(f"Skipping (already in manifest): {url}")
            continue

        # Create per-pollutant-year dirs
        dest_raw = RAW_DIR / pol / str(yr)
        dest_ext = EXTRACT_DIR / pol / str(yr)

        try:
            fpath = download_file(session, url, dest_raw)
            local_csv_paths = []
            if fpath.suffix.lower() == ".zip":
                extracted = extract_if_zip(fpath, dest_ext)
                local_csv_paths.extend([str(p) for p in extracted])
            elif fpath.suffix.lower() == ".csv":
                local_csv_paths.append(str(fpath))
            else:
                logging.info(f"Unsupported filetype (skipping): {fpath}")
                continue

            manifest_rec = {
                "pollutant": pol,
                "year": yr,
                "source_url": url,
                "source_filename": fpath.name,
                "local_file": str(fpath),
                "local_csv_paths": local_csv_paths,
                "timestamp": time.time(),
                "page": BASE_URL,
            }
            write_manifest_record(manifest_rec)
            logging.info(f"Recorded manifest for {pol} {yr}: {url}")

            # be polite
            time.sleep(0.3 + random.random() * 0.4)

        except Exception as e:
            logging.warning(f"Failed to process {url}: {e}")



# ----------------------------
# CSV reading and combining
# ----------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Make columns case-insensitive, whitespace-free
    rename_map = {c: re.sub(r"\s+", "_", c.strip().lower()) for c in df.columns}
    df = df.rename(columns=rename_map)
    # Common aliases: promote consistent coord names if possible
    coord_map = {
        "easting": ["easting", "eastings", "x", "e"],
        "northing": ["northing", "northings", "y", "n"],
        "longitude": ["longitude", "long", "lon", "x_lon", "xlong", "xcoord_lon"],
        "latitude": ["latitude", "lat", "y_lat", "ylat", "ycoord_lat"],
        "grid_ref": ["gridref", "grid_ref", "grid-reference", "gridreference", "grid_refe"],
    }
    for canonical, alts in coord_map.items():
        # If canonical already present, skip
        if canonical in df.columns:
            continue
        for alt in alts:
            if alt in df.columns:
                df = df.rename(columns={alt: canonical})
                break
    return df


def read_csv_tolerant(path: Path, skip: int = 5) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, low_memory=False, encoding=enc, skiprows=skip)
            return df
        except Exception:
            continue
    # Try excel if CSV fails (some PCM releases used XLSX occasionally)
    if path.suffix.lower() in [".xls", ".xlsx"]:
        try:
            return pd.read_excel(path)
        except Exception:
            pass
    raise RuntimeError(f"Failed to read CSV: {path}")

def combine_csvs(manifest: list[dict], out_csv: Path):
    all_paths = []
    for rec in manifest:
        # only use CSV files (either direct or extracted)
        for p in rec.get("local_csv_paths", []):
            if str(p).lower().endswith(".csv") and Path(p).exists():
                all_paths.append((Path(p), rec["pollutant"], rec["year"], rec["source_url"], rec.get("source_filename")))
    if not all_paths:
        logging.warning("No CSV paths found to combine.")
        return

     # Save
    logging.info(f"Writing combined CSV -> {out_csv}")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    out_created = False
    for p, pol, yr, src_url, src_file in tqdm(all_paths, desc="Reading CSVs"):
        try:
            df = read_csv_tolerant(p)
            df = normalize_columns(df)
            # Identify the current name of the fourth column (index 3)
            # Based on the previous output, it should be 'unnamed:_3'
            current_fourth_column_name = df.columns[3]

            # Rename the fourth column to 'amount'
            df.rename(columns={current_fourth_column_name: 'amount'}, inplace=True)

            # Add metadata columns
            df["pollutant"] = pol
            df["year"] = yr
            df["source_file"] = src_file or p.name

            # Filter out the missing data
            df = df[df['amount']!="MISSING"]
            if not out_created:
                df.to_csv(out_csv, index=False, header=True)
                out_created = True
            else:
                df.to_csv(out_csv, mode='a', index=False, header=False)
        except Exception as e:
            logging.warning(f"Skipping {p} due to read error: {e}")
    logging.info("Files combined!")
    return





def build_csvs(out_csv: Path = Path('UK_annual_pollution.csv')):
    # Reload manifest (now including what we just added)
    manifest = load_manifest()
    combine_csvs(manifest, out_csv)

    # Quick summary
    try:
        df = pd.read_csv(out_csv, nrows=1000)  # sample to list columns
        logging.info(f"Combined file columns (sample): {list(df.columns)}")
    except Exception:
        pass

    logging.info("Done.")

def filter_scotland(out_csv: Path = Path('UK_annual_pollution.csv'), 
                    scotland_csv: Path = Path('scotland_annual_pollution.csv'), 
                    scot_lat: float = 55.0):
    # Import the filtering function from scotland_filter_pollution.py

    # 1. Load the CSV file
    # Replace 'haduk_data.csv' with your actual filename
    df = pd.read_csv(out_csv)

    # Ensure the coordinate columns are numeric and named correctly
    # HadUK files often use 'easting' and 'northing' or similar variations
    # Adjust column names if your CSV uses different headers (e.g., 'Easting', 'Northing')
    easting_col = 'easting'
    northing_col = 'northing'

    # Check if columns exist (case-insensitive check helper)
    cols_lower = [c.lower() for c in df.columns]
    if easting_col.lower() not in cols_lower:
        raise ValueError(f"Column '{easting_col}' not found. Available columns: {df.columns}")
    if northing_col.lower() not in cols_lower:
        # Find the actual case-matched name
        easting_col = [c for c in df.columns if c.lower() == easting_col.lower()][0]
        northing_col = [c for c in df.columns if c.lower() == northing_col.lower()][0]

    # 2. Create a GeoDataFrame from the Pandas DataFrame
    # The British National Grid uses EPSG:27700
    geometry = [Point(xy) for xy in zip(df[easting_col], df[northing_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:27700")

    # 3. Reproject to WGS84 (Latitude/Longitude) - EPSG:4326
    gdf_wgs84 = gdf.to_crs(epsg=4326)

    # 4. Extract Latitude and Longitude into new columns for convenience
    # In GeoPandas, geometry.x is Longitude and geometry.y is Latitude
    gdf_wgs84['longitude'] = gdf_wgs84.geometry.x
    gdf_wgs84['latitude'] = gdf_wgs84.geometry.y

    # 5. Filter for Latitude > 55 (Approximate Scottish region)
    scotland_df = gdf_wgs84[gdf_wgs84['latitude'] > scot_lat]

    # Output results
    logging.info(f"Original records: {len(df)}")
    logging.info(f"Records in Scottish region (Lat > {scot_lat}): {len(scotland_df)}")

    # Display the first few rows of the filtered data
    logging.info("Filtered data (first 5 rows):")
    logging.info(scotland_df.head())

    # If you need to save the filtered result back to a standard CSV (without geometry object issues)
    # We select the original columns plus the new lat/lon columns
    output_columns = list(df.columns) + ['longitude', 'latitude']
    scotland_df[output_columns].to_csv(scotland_csv, index=False)


links, seen_urls = get_links()

download_csvs(links, seen_urls)

build_csvs()

filter_scotland()