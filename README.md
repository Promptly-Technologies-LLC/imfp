# imfp

[![Tests](https://github.com/Promptly-Technologies-LLC/imfp/actions/workflows/test.yml/badge.svg)](https://github.com/Promptly-Technologies-LLC/imfp/actions/workflows/test.yml)
[![PyPI Version](https://img.shields.io/pypi/v/imfp.svg)](https://pypi.python.org/pypi/imfp)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

`imfp`, by Christopher C. Smith, is a Python package for downloading data from the [International Monetary Fund's](http://data.imf.org/) RESTful JSON API.

**[📚 Full Documentation](https://promptlytechnologies.com/imfp/)**

## Installation

```bash
pip install -q --upgrade imfp
```

## Quick Start

`imfp` follows the [econdataverse](https://econdataverse.org/) conventions, mirroring the R package [imfapi](https://github.com/Teal-Insights/r-imfapi). Fetching data takes four steps, one per function:

```python
import imfp

# 1. Find a dataset
dataflows = imfp.imf_get_dataflows()

# 2. See how it can be filtered
dimensions = imfp.imf_get_datastructure("PCPS")

# 3. Find valid codes for those dimensions
codes = imfp.imf_get_codelists(["INDICATOR", "FREQUENCY"], "PCPS")

# 4. Fetch the data
df = imfp.imf_get(
    "PCPS",
    dimensions={
        "INDICATOR": ["PCOAL"],
        "DATA_TRANSFORMATION": ["INDEX"],
        "FREQUENCY": ["A"],
    },
)
```

Dimensions can also be passed as keyword arguments:

```python
df = imfp.imf_get("PCPS", indicator="PCOAL", data_transformation="INDEX", frequency="A")
```

## Upgrading from 1.x

Version 2.0.0 replaces the old four-function API. The old names still work but emit a `DeprecationWarning`, and will be removed in 3.0.0.

| imfp 1.x | imfp 2.0 |
|---|---|
| `imf_databases()` | `imf_get_dataflows()` |
| `imf_parameters(db)` | `imf_get_codelists(dims, db)` |
| `imf_parameter_defs(db)` | `imf_get_datastructure(db)` |
| `imf_dataset(db, ...)` | `imf_get(db, ...)` |

See the [migration guide](https://promptlytechnologies.com/imfp/user-guide/migration.html) for argument-by-argument details.

## Key Features

- Comprehensive access to IMF's extensive economic databases
- Dataset, dimension, and code discovery
- Tidy `pandas` DataFrame output, with numeric observation values
- Rate limit and bandwidth management

## Contributing

We welcome contributions to improve `imfp`! Here's how you can help:

1. If you find a bug, please open an issue
2. To fix a bug:
   - Fork and clone the repository and open a terminal in the repository directory
   - Install [uv](https://astral.sh/setup-uv/) with `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Install the dependencies with `uv sync`
   - Install a git hook to enforce conventional commits with `curl -o- https://raw.githubusercontent.com/chriscarrollsmith/conventional-commits-git-hook/master/scripts/install.sh | sh`
   - Create a fix, commit it with an ["Angular-style Conventional Commit"](https://www.conventionalcommits.org/en/v1.0.0-beta.4/) message, and push it to your fork
   - Open a pull request to our `main` branch

Note that if you want to change and preview the documentation, you will need to install the [Quarto CLI tool](https://quarto.org/docs/download/) and run `uv run great-docs build` (or `uv run great-docs preview`).

Version incrementing, package building, testing, changelog generation, documentation rendering, publishing to PyPI, and Github release creation is handled automatically by the GitHub Actions workflow based on the commit messages.
