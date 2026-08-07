---
name: imfp
description: >
  Python package for downloading economic data from the International Monetary Fund SDMX 3.0 API, following econdataverse conventions. Use when writing Python code that uses the imfp package.
license: MIT
compatibility: Requires Python >=3.10.
---

# imfp

Python package for downloading economic data from the International Monetary Fund SDMX 3.0 API, following econdataverse conventions.

## Installation

```bash
pip install imfp
```

## API overview

### Fetching Data

The econdataverse-style workflow: discover a dataset, inspect how it can be filtered, look up valid codes, then request observations.


- `imf_get_dataflows`: List every dataset published through the IMF Data API
- `imf_get_datastructure`: List the dimensions a dataset can be filtered on
- `imf_get_codelists`: Look up the valid codes for one or more of a dataset's dimensions
- `imf_get`: Fetch observations from an IMF dataset

### Configuration

Settings that affect how requests are made

- `set_imf_app_name`: Set the IMF Application Name
- `set_imf_wait_time`: Set the IMF wait time as an environment variable

### Deprecated

The pre-2.0 interface. These still work but emit a DeprecationWarning and will be removed in imfp 3.0.0. See the migration guide.


- `imf_databases`: List IMF database IDs and descriptions
- `imf_parameters`: List input parameters and available parameter values for use in
- `imf_parameter_defs`: Get text descriptions of input parameters used in making API
- `imf_dataset`: Download a data series from the IMF

## Resources

- [Full documentation](https://promptlytechnologies.com/imfp/)
- [llms.txt](llms.txt) — Indexed API reference for LLMs
- [llms-full.txt](llms-full.txt) — Comprehensive documentation for LLMs
