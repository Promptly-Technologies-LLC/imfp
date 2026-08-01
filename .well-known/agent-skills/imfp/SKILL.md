---
name: imfp
description: >
  Python package for downloading economic data from the International Monetary Fund JSON RESTful API endpoint. Use when writing Python code that uses the imfp package.
license: MIT
compatibility: Requires Python >=3.10.
---

# imfp

Python package for downloading economic data from the International Monetary Fund JSON RESTful API endpoint.

## Installation

```bash
pip install imfp
```

## API overview

### Functions

Public functions for discovering IMF databases and downloading data

- `imf_databases`: List IMF database IDs and descriptions
- `imf_parameters`: List input parameters and available parameter values for use in
- `imf_parameter_defs`: Get text descriptions of input parameters used in making API
- `imf_dataset`: Download a data series from the IMF
- `set_imf_app_name`: Set the IMF Application Name
- `set_imf_wait_time`: Set the IMF wait time as an environment variable

## Resources

- [Full documentation](https://promptlytechnologies.com/imfp/)
- [llms.txt](llms.txt) — Indexed API reference for LLMs
- [llms-full.txt](llms-full.txt) — Comprehensive documentation for LLMs
