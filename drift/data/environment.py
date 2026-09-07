"""Environmental Forcing Data Ingestion and Adapter Module.

Provides interfaces for loading, parsing, and spatial-temporal indexing of
surface ocean currents and surface wind fields from NetCDF datasets for drift modeling.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xarray as xr


class EnvironmentalDataLoader:
    """Interface for querying and loading environmental forcing datasets (winds & ocean currents)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize environmental data loader with configuration parameters.

        Args:
            config: Optional dictionary containing dataset paths.
                Recognized keys include 'era5_path' and 'copernicus_path'.

        Raises:
            FileNotFoundError: If ERA5 or Copernicus dataset files do not exist.
        """
        config = config or {}
        project_root = Path(__file__).resolve().parents[2]

        era5_setting = config.get("era5_path") or config.get("era5_file")
        if era5_setting:
            self.era5_path = Path(era5_setting)
        else:
            self.era5_path = project_root / "drift" / "data" / "era5_test.nc"

        copernicus_setting = config.get("copernicus_path") or config.get("copernicus_file")
        if copernicus_setting:
            self.copernicus_path = Path(copernicus_setting)
        else:
            self.copernicus_path = project_root / "drift" / "data" / "copernicus_currents_test.nc"

        if not self.era5_path.is_file():
            raise FileNotFoundError(f"ERA5 test dataset file not found at: {self.era5_path}")

        if not self.copernicus_path.is_file():
            raise FileNotFoundError(f"Copernicus ocean currents test dataset file not found at: {self.copernicus_path}")

    def load_surface_winds(
        self,
        time_range: Tuple[str, str],
        bounding_box: Tuple[float, float, float, float]
    ) -> xr.Dataset:
        """Load surface wind vectors (u10, v10) for a given spatio-temporal extent.

        Args:
            time_range: Start and end ISO 8601 timestamps (start_utc, end_utc).
            bounding_box: Bounding box tuple (min_lon, min_lat, max_lon, max_lat).

        Returns:
            xr.Dataset: In-memory xarray Dataset containing u10 and v10 variables.

        Raises:
            KeyError: If u10 or v10 variables are missing from dataset.
        """
        min_lon, min_lat, max_lon, max_lat = bounding_box

        with xr.open_dataset(self.era5_path) as ds:
            if "u10" not in ds.data_vars or "v10" not in ds.data_vars:
                raise KeyError("ERA5 dataset missing required wind variables 'u10' or 'v10'.")

            time_dim = "valid_time" if "valid_time" in ds.coords or "valid_time" in ds.dims else "time"
            lat_dim = "latitude" if "latitude" in ds.coords else "lat"
            lon_dim = "longitude" if "longitude" in ds.coords else "lon"

            lat_vals = ds[lat_dim].values
            if len(lat_vals) > 1 and lat_vals[0] > lat_vals[-1]:
                lat_slice = slice(max_lat, min_lat)
            else:
                lat_slice = slice(min_lat, max_lat)

            lon_vals = ds[lon_dim].values
            if len(lon_vals) > 1 and lon_vals[0] > lon_vals[-1]:
                lon_slice = slice(max_lon, min_lon)
            else:
                lon_slice = slice(min_lon, max_lon)

            sel_kwargs = {
                lat_dim: lat_slice,
                lon_dim: lon_slice,
            }
            if time_dim in ds.coords or time_dim in ds.dims:
                sel_kwargs[time_dim] = slice(time_range[0], time_range[1])

            subset_ds = ds.sel(**sel_kwargs).load()

        return subset_ds

    def load_ocean_currents(
        self,
        time_range: Tuple[str, str],
        bounding_box: Tuple[float, float, float, float]
    ) -> xr.Dataset:
        """Load surface ocean current vectors (uo, vo) for a given spatio-temporal extent.

        Args:
            time_range: Start and end ISO 8601 timestamps (start_utc, end_utc).
            bounding_box: Bounding box tuple (min_lon, min_lat, max_lon, max_lat).

        Returns:
            xr.Dataset: In-memory xarray Dataset containing surface uo and vo variables.

        Raises:
            KeyError: If uo or vo variables are missing from dataset.
        """
        min_lon, min_lat, max_lon, max_lat = bounding_box

        with xr.open_dataset(self.copernicus_path) as ds:
            if "uo" not in ds.data_vars or "vo" not in ds.data_vars:
                raise KeyError("Copernicus currents dataset missing required variables 'uo' or 'vo'.")

            time_dim = "time" if "time" in ds.coords or "time" in ds.dims else "valid_time"
            lat_dim = "latitude" if "latitude" in ds.coords else "lat"
            lon_dim = "longitude" if "longitude" in ds.coords else "lon"

            if "depth" in ds.dims:
                ds = ds.isel(depth=0)

            lat_vals = ds[lat_dim].values
            if len(lat_vals) > 1 and lat_vals[0] > lat_vals[-1]:
                lat_slice = slice(max_lat, min_lat)
            else:
                lat_slice = slice(min_lat, max_lat)

            lon_vals = ds[lon_dim].values
            if len(lon_vals) > 1 and lon_vals[0] > lon_vals[-1]:
                lon_slice = slice(max_lon, min_lon)
            else:
                lon_slice = slice(min_lon, max_lon)

            sel_kwargs = {
                lat_dim: lat_slice,
                lon_dim: lon_slice,
            }
            if time_dim in ds.coords or time_dim in ds.dims:
                sel_kwargs[time_dim] = slice(time_range[0], time_range[1])

            subset_ds = ds.sel(**sel_kwargs).load()

        return subset_ds

    def get_opendrift_readers(self) -> List[Any]:
        """Instantiate and return OpenDrift CF-generic NetCDF reader instances.

        Returns:
            List[Any]: List containing OpenDrift Reader instances in order:
                [reader_era5, reader_copernicus]
        """
        from opendrift.readers.reader_netCDF_CF_generic import Reader

        reader_era5 = Reader(str(self.era5_path))
        reader_copernicus = Reader(str(self.copernicus_path))

        return [reader_era5, reader_copernicus]


