#!/usr/bin/env python3
"""
Combine climate NetCDF files from HadUK-Grid into a single CSV or Parquet file with columns:
    x_grid, y_grid, type_of_reading, year, month, value
Filter to Scotland records by using only records north of Latitude 55.0 (approx north of Newcastle).
"""
import os
import sys
import glob
import numpy as np
import pandas as pd
import xarray as xr
import logging


# Optional: only needed if the dataset lacks a 2D 'latitude' variable
try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except Exception:
    HAS_PYPROJ = False

# ----------------------------
# Configuration
# ----------------------------
BASE_DIR = "haduk_grid_downloads"  # root directory containing subfolders like tas/, groundfrost/, etc.
OUTFILE = "scotland_monthly_climate.csv"  # change to .parquet for Parquet output
LAT_MIN = 55.0  # "north of Newcastle" ~55N; adjust if you want stricter/looser Scotland mask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)    


# If writing Parquet, chunk processing will append row groups
WRITE_PARQUET = OUTFILE.lower().endswith(".parquet")


def find_main_data_var(ds: xr.Dataset) -> str:
    """Pick the main numeric data variable with (time, y, x)-like dims."""
    ignore = {"latitude", "longitude", "crs", "rotated_pole", "lambert_azimuthal_equal_area"}
    candidates = []
    for v in ds.data_vars:
        if v in ignore:
            continue
        da = ds[v]
        if da.ndim >= 3 and "time" in da.dims and np.issubdtype(da.dtype, np.number):
            candidates.append((v, da.size))
    if not candidates:
        # fallback: any numeric with 'time' in dims
        for v in ds.data_vars:
            da = ds[v]
            if "time" in da.dims and np.issubdtype(da.dtype, np.number):
                candidates.append((v, da.size))
    if not candidates:
        raise ValueError("Could not identify main data variable (no numeric variable with time dimension).")
    # choose the largest by element count
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def get_xy_dim_names(da: xr.DataArray):
    """Infer the grid dimension names (y, x)."""
    dims = list(da.dims)
    # Expect 3 dims: (time, y, x) in some order
    grid_dims = [d for d in dims if d != "time"]
    if len(grid_dims) == 2:
        # Try to return as (y, x)
        if "y" in grid_dims and "x" in grid_dims:
            return "y", "x"
        # Heuristics for HadUK-Grid aliases
        if "projection_y_coordinate" in grid_dims and "projection_x_coordinate" in grid_dims:
            return "projection_y_coordinate", "projection_x_coordinate"
        if "grid_latitude" in grid_dims and "grid_longitude" in grid_dims:
            return "grid_latitude", "grid_longitude"
        # Default order: first is y-like, second x-like
        return grid_dims[0], grid_dims[1]
    raise ValueError(f"Unexpected data dims: {dims}. Expected (time, y, x)-like.")


def get_lat_2d(ds: xr.Dataset, ydim: str, xdim: str) -> xr.DataArray:
    """Return 2D latitude array matching (ydim, xdim). Use ds['latitude'] if present; else compute from x/y with pyproj."""
    if "latitude" in ds.variables and set(ds["latitude"].dims) == {ydim, xdim}:
        return ds["latitude"]

    # Try computing from 1D projected coords using pyproj
    if (ydim in ds.coords) and (xdim in ds.coords):
        if not HAS_PYPROJ:
            raise RuntimeError("Dataset lacks 2D 'latitude' and pyproj is not installed. pip install pyproj")
        # Assume British National Grid (OSGB36: EPSG:27700) for HadUK-Grid 1km
        x1d = ds[xdim].values
        y1d = ds[ydim].values
        xx, yy = np.meshgrid(x1d, y1d)
        transformer = Transformer.from_crs(27700, 4326, always_xy=True)  # E,N -> lon,lat
        lon2d, lat2d = transformer.transform(xx, yy)
        lat_da = xr.DataArray(lat2d, dims=(ydim, xdim), coords={ydim: ds[ydim], xdim: ds[xdim]}, name="latitude")
        return lat_da

    raise RuntimeError("Cannot obtain latitude grid: no 2D 'latitude' and missing 1D x/y coordinates to compute it.")


def get_type_from_path(path: str) -> str:
    """Infer reading type from parent directory name (e.g., 'tas', 'groundfrost')."""
    parent = os.path.basename(os.path.dirname(path))
    return parent


def extract_year_month(series_or_index):
    """Robustly derive year/month whether time is datetime64 or cftime."""
    # Try vectorized pandas first
    try:
        s = pd.to_datetime(series_or_index)
        return s.dt.year.to_numpy(), s.dt.month.to_numpy()
    except Exception:
        # Fallback to python attribute access (cftime objects)
        years = np.array([getattr(t, "year") for t in series_or_index])
        months = np.array([getattr(t, "month") for t in series_or_index])
        return years, months


def process_file(nc_path: str) -> pd.DataFrame:
    reading_type = get_type_from_path(nc_path)

    # Open lazily; we don't need dask here but xarray will read on demand
    ds = xr.open_dataset(nc_path, decode_times=True)

    # Identify main data variable and grid dims
    var_name = find_main_data_var(ds)
    da = ds[var_name]

    ydim, xdim = get_xy_dim_names(da)

    # Get 2D latitude and build mask for Scotland-ish (north of Newcastle)
    lat2d = get_lat_2d(ds, ydim, xdim)
    mask = lat2d >= LAT_MIN

    # Apply mask and drop non-matching grid points
    da_masked = da.where(mask, drop=True).rename("value")

    # Convert to tidy DataFrame: columns -> time, ydim, xdim, value
    df = da_masked.to_dataframe().reset_index()

    # Derive year and month
    years, months = extract_year_month(df["time"])
    df["year"] = years
    df["month"] = months

    # Keep only required columns and rename x/y to x_grid/y_grid (use coordinate values, not indices)
    # Ensure we use coordinate columns if they exist; after reset_index(), ydim/xdim columns hold coordinate values.
    cols_keep = {xdim: "x_grid", ydim: "y_grid", "value": "value", "year": "year", "month": "month"}
    missing = [c for c in (xdim, ydim, "value", "year", "month") if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing expected columns after conversion: {missing}")

    df = df[[xdim, ydim, "year", "month", "value"]].rename(columns=cols_keep)
    df = df[~np.isnan(df['value'])]  # Optional: skip rows where value is NaN
 
    df.insert(2, "type_of_reading", reading_type)  # x_grid, y_grid, type_of_reading, year, month, value

    return df


def main():
    nc_files = sorted(glob.glob(os.path.join(BASE_DIR, "**", "*.nc"), recursive=True))
    if not nc_files:
        print(f"No .nc files found under {BASE_DIR}", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(OUTFILE):
        print(f"Output file {OUTFILE} already exists. Please remove it before running to avoid appending to old data.", file=sys.stderr)
        sys.exit(1)
    logging.info(f"Found {len(nc_files)} NetCDF files. Processing with LAT_MIN={LAT_MIN} ...")
#  rainfall_hadukgrid_uk_1km_mon_201301-201312
    if WRITE_PARQUET:
        import pyarrow as pa
        import pyarrow.parquet as pq

        writer = None
        schema = None
        try:
            for i, fp in enumerate(nc_files, 1):
                logging.info(f"[{i}/{len(nc_files)}] {fp}")
                df = process_file(fp)

                # Define a stable column order
                df = df[["x_grid", "y_grid", "type_of_reading", "year", "month", "value"]]

                # Initialize or append Parquet row group
                table = pa.Table.from_pandas(df, preserve_index=False)
                if writer is None:
                    schema = table.schema
                    writer = pq.ParquetWriter(OUTFILE, schema, compression="zstd")
                writer.write_table(table)
            if writer is not None:
                writer.close()
            logging.info(f"Wrote Parquet to {OUTFILE}")
        finally:
            if writer is not None:
                writer.close()
    else:
        # CSV append mode
        header_written = os.path.exists(OUTFILE) and os.path.getsize(OUTFILE) > 0
        num_files = 0
        for i, fp in enumerate(nc_files, 1):
            logging.info(f"[{i}/{len(nc_files)}] {fp}")
            try:
                df = process_file(fp)
                num_files += 1
            except Exception as e:
                logging.info(f"Error processing {fp}: {e}", file=sys.stderr)
                continue

            # Column order
            df = df[["x_grid", "y_grid", "type_of_reading", "year", "month", "value"]]
            df.to_csv(OUTFILE, mode="a", index=False, header=not header_written)
            header_written = True
        logging.info(f"Wrote CSV to {OUTFILE} ({num_files} files processed)")


if __name__ == "__main__":
    main()
