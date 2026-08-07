"""Python client for the International Monetary Fund's SDMX 3.0 Data API.

The primary interface follows the `econdataverse <https://econdataverse.org/>`_
conventions: ``imf_get_dataflows`` -> ``imf_get_datastructure`` ->
``imf_get_codelists`` -> ``imf_get``. See :mod:`imfp.api`.

The older ``imf_databases`` / ``imf_parameters`` / ``imf_parameter_defs`` /
``imf_dataset`` functions still work but are deprecated, and will be removed in
imfp 3.0.0.
"""

from .admin import set_imf_app_name, set_imf_wait_time
from .api import imf_get, imf_get_codelists, imf_get_dataflows, imf_get_datastructure
from .data import imf_databases, imf_dataset, imf_parameter_defs, imf_parameters
from .utils import (
    _download_parse,
    _imf_dimensions,
    _imf_get,
    _imf_metadata,
    _min_wait_time_limited,
)

__all__ = [
    "_imf_get",
    "_min_wait_time_limited",
    "_imf_wait_time",
    "_download_parse",
    "_imf_metadata",
    "_imf_dimensions",
    # Econdataverse-style API
    "imf_get",
    "imf_get_codelists",
    "imf_get_dataflows",
    "imf_get_datastructure",
    # Deprecated, removal in 3.0.0
    "imf_databases",
    "imf_parameters",
    "imf_parameter_defs",
    "imf_dataset",
    "set_imf_app_name",
    "set_imf_wait_time",
]
