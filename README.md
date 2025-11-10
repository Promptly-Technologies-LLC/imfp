# imfp

[![Tests](https://github.com/Promptly-Technologies-LLC/imfp/actions/workflows/test.yml/badge.svg)](https://github.com/Promptly-Technologies-LLC/imfp/actions/workflows/test.yml)
[![PyPI Version](https://img.shields.io/pypi/v/imfp.svg)](https://pypi.python.org/pypi/imfp)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`imfp`, by Christopher C. Smith, is a Python package for downloading data from the [International Monetary Fund's](http://data.imf.org/) RESTful JSON API.

**[📚 Full Documentation](https://promptlytechnologies.com/imfp/)**

## Installation

```bash
pip install -q --upgrade imfp
```

## Quick Start

```python
import imfp

# Get list of available databases
databases = imfp.imf_databases()

# Get parameters for a specific database (e.g., PCPS - Primary Commodity Price System)
params = imfp.imf_parameters("PCPS")

# Fetch data with specific parameters
df = imfp.imf_dataset(
    database_id="PCPS",
    frequency=["A"],
    start_year=2000,
    end_year=2015
)
```

## Key Features

- Comprehensive access to IMF's extensive economic databases
- Parameter discovery
- Rate limit and bandwidth management
- Returns data in pandas DataFrames

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

Note that if you want to change and preview the documentation, you will need to install the [Quarto CLI tool](https://quarto.org/docs/download/).

Version incrementing, package building, testing, changelog generation, documentation rendering, publishing to PyPI, and Github release creation is handled automatically by the GitHub Actions workflow based on the commit messages.
