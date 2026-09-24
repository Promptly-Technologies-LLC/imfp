# Fetching Data


# Making a Request

[imf_get](../reference/imf_get.md#imfp.imf_get) takes a dataflow ID and the dimension filters you found with [`imf_get_codelists`](parameters.md):


``` python
import imfp

df = imfp.imf_get(
    "PCPS",
    dimensions={
        "INDICATOR": ["PCOAL"],
        "DATA_TRANSFORMATION": ["INDEX"],
        "FREQUENCY": ["A"],
    },
)
df.head()
```


|  | COUNTRY | INDICATOR | DATA_TRANSFORMATION | FREQUENCY | TIME_PERIOD | OBS_VALUE | SCALE | DERIVATION_TYPE |
|----|----|----|----|----|----|----|----|----|
| 0 | G001 | PCOAL | INDEX | A | 1992 | 49.892138 | 0 | R |
| 1 | G001 | PCOAL | INDEX | A | 1993 | 43.279151 | 0 | R |
| 2 | G001 | PCOAL | INDEX | A | 1994 | 45.213931 | 0 | R |
| 3 | G001 | PCOAL | INDEX | A | 1995 | 55.433711 | 0 | R |
| 4 | G001 | PCOAL | INDEX | A | 1996 | 53.179458 | 0 | R |


Dimensions you do not mention are wildcarded, so the request above returns coal for every country in the dataset.


# Two Ways to Pass Dimensions

Filters can go in the `dimensions` dict, or in as keyword arguments, whichever reads better. Keyword names are matched case-insensitively:


``` python
df = imfp.imf_get("PCPS", indicator="PCOAL", data_transformation="INDEX", frequency="A")
df.head(3)
```


|  | COUNTRY | INDICATOR | DATA_TRANSFORMATION | FREQUENCY | TIME_PERIOD | OBS_VALUE | SCALE | DERIVATION_TYPE |
|----|----|----|----|----|----|----|----|----|
| 0 | G001 | PCOAL | INDEX | A | 1992 | 49.892138 | 0 | R |
| 1 | G001 | PCOAL | INDEX | A | 1993 | 43.279151 | 0 | R |
| 2 | G001 | PCOAL | INDEX | A | 1994 | 45.213931 | 0 | R |


A single code can be given as a bare string; several go in a list:


``` python
df = imfp.imf_get(
    "PCPS",
    indicator=["PCOAL", "PNGAS"],
    data_transformation="INDEX",
    frequency="A",
)
sorted(df["INDICATOR"].unique())
```


    ['PCOAL', 'PNGAS']


Passing the same dimension both ways is an error rather than a silent precedence rule:


``` python
try:
    imfp.imf_get("PCPS", dimensions={"INDICATOR": "PCOAL"}, indicator="PNGAS")
except ValueError as e:
    print(e)
```


    Dimension 'INDICATOR' was supplied more than once. Pass each dimension either in `dimensions` or as a keyword argument, not both.


# The Returned Data

[imf_get](../reference/imf_get.md#imfp.imf_get) returns tidy data -- one observation per row, one variable per column:


``` python
df.dtypes
```


    COUNTRY                 object
    INDICATOR               object
    DATA_TRANSFORMATION     object
    FREQUENCY               object
    TIME_PERIOD             object
    OBS_VALUE              float64
    SCALE                   object
    DERIVATION_TYPE         object
    dtype: object


There is one column per dimension, named with its SDMX dimension ID, plus two more:

- `TIME_PERIOD` -- the period of the observation, as a string
- `OBS_VALUE` -- the observed value, as a float

`OBS_VALUE` arrives already converted to `float64`, with non-numeric missing-value flags turned into `NaN`.

`TIME_PERIOD` stays a string because its format depends on the frequency of the series: `"2000"` for annual data, `"2000-Q1"` for quarterly, `"2000-M01"` for monthly. See [Suggestions for Usage](usage.md#time-period-conversion) for conversion recipes.


## Attributes: Units, Scale, and Status

After `OBS_VALUE` come the dataset's SDMX *attributes*, which describe how to read each value. Which ones appear depends on the dataset, but the most useful are:

- `UNIT` -- the unit of measure, e.g. `PT` (percent), `IX` (index), `XDC` (domestic currency), `USD`
- `SCALE` -- the power of ten the value is expressed in: `"0"` for units, `"6"` for millions, `"9"` for billions
- `STATUS` -- an observation-level flag, e.g. `E` for estimated or `P` for provisional
- `DERIVATION_TYPE` -- whether a value was observed or derived


``` python
growth = imfp.imf_get("WEO", country="USA", indicator="NGDP_RPCH", frequency="A")
growth[["INDICATOR", "TIME_PERIOD", "OBS_VALUE", "UNIT", "SCALE"]].head(3)
```


|     | INDICATOR | TIME_PERIOD | OBS_VALUE | UNIT | SCALE |
|-----|-----------|-------------|-----------|------|-------|
| 0   | NGDP_RPCH | 1980        | -0.256666 | PT   | 0     |
| 1   | NGDP_RPCH | 1981        | 2.537436  | PT   | 0     |
| 2   | NGDP_RPCH | 1982        | -1.803070 | PT   | 0     |


An attribute appears as a column only when it has a value somewhere in the response, and is `NaN` for rows it does not apply to. Attributes can vary between series, so check `UNIT` and `SCALE` before combining series or comparing across countries. In rare cases an attribute has the same ID as a dimension; it is then suffixed with `_ATTRIBUTE`.

Not every dataset reports `UNIT`. The coal price index above has no `UNIT` column, for example; its unit is implied by the `DATA_TRANSFORMATION` dimension. Look up such codes with [imf_get_codelists](../reference/imf_get_codelists.md#imfp.imf_get_codelists).

Pass `attributes=False` for just the dimensions, `TIME_PERIOD`, and `OBS_VALUE`:


``` python
imfp.imf_get("PCPS", indicator="PCOAL", frequency="A", attributes=False)
```


# Time Filtering

`start_period` and `end_period` bound the time window. They accept a year, a quarter, or a month:


``` python
imfp.imf_get("GFS_SOO", country="ABW", frequency="A", start_period=2000, end_period=2015)
imfp.imf_get("QNEA", country="USA", frequency="Q", start_period="2010-Q1")
imfp.imf_get("CPI", country="USA", frequency="M", start_period="2010-01")
```


A bare year is widened to cover the whole year at the frequency you asked for: with `frequency="Q"`, `start_period=2010` means `2010-Q1` and `end_period=2015` means `2015-Q4`. When you request several frequencies at once, or none, the end bound widens far enough to keep every sub-annual period in that year.

> **Warning: Not every agency supports time filtering**
>
> Time filtering happens server-side, and at present only datasets published by `IMF.STA` support it. For datasets published by other departments, [imf_get](../reference/imf_get.md#imfp.imf_get) warns you and returns the full time range:
>
> <div id="0b4ce05e" class="cell" data-execution_count="9">
>
> ``` python
> df = imfp.imf_get(
>     "PCPS", indicator="PCOAL", data_transformation="INDEX", frequency="A",
>     start_period=2000, end_period=2015,
> )
> ```
>
> <div class="cell-output cell-output-stderr">
>
>     /home/runner/work/imfp/imfp/imfp/utils.py:908: UserWarning: Agency IMF.RES does not support time filters; time window will be ignored.
>       warn(
>
> <div id="empty-results" class="section level1">
>
> # Empty Results
>
> A query that matches nothing returns an empty DataFrame and warns, rather than raising. This keeps a query that legitimately has no data from breaking an automated pipeline:
>
> <div id="368777e9" class="cell" data-execution_count="11">
>
> ``` python
> df = imfp.imf_get("PCPS", indicator="PCOAL", frequency="A", data_transformation="USD")
> if df.empty:
>     print("No observations; try relaxing the filters.")
> ```
>
> </div>
>
> The usual causes are a code that is valid for the dimension but has no data for the rest of your filters, or a combination of filters that is individually valid but jointly empty. Relax one dimension at a time to find out which.
>
> <div id="validating-codes" class="section level1">
>
> # Validating Codes
>
> [imf_get](../reference/imf_get.md#imfp.imf_get) checks that the *dimensions* you name belong to the dataset:
>
> <div id="e13488b0" class="cell" data-execution_count="12">
>
> ``` python
> try:
>     imfp.imf_get("PCPS", not_a_dimension="X")
> except ValueError as e:
>     print(e)
> ```
>
> <div class="cell-output cell-output-stdout">
>
>     Unknown dimension(s): NOT_A_DIMENSION. Available dimensions: COUNTRY, DATA_TRANSFORMATION, FREQUENCY, INDICATOR
>
> </div>
>
> </div>
>
> It does not check the *codes*, because doing so would mean downloading every codelist before every request -- often slower than the request itself. The API is the authority on which codes are valid; use [imf_get_codelists](../reference/imf_get_codelists.md#imfp.imf_get_codelists) when you want to check ahead of time.
>
> <div id="inspecting-the-request" class="section level1">
>
> # Inspecting the Request
>
> `print_url=True` prints the URL being requested, which is the most useful thing to include when reporting a problem with a particular query:
>
> <div id="fac889e5" class="cell" data-execution_count="13">
>
> ``` python
> df = imfp.imf_get(
>     "PCPS", indicator="PCOAL", data_transformation="INDEX", frequency="A",
>     print_url=True,
> )
> ```
>
> <div class="cell-output cell-output-stdout">
>
>     https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.RES/PCPS/+/*.PCOAL.INDEX.A?dimensionAtObservation=TIME_PERIOD&attributes=dsd&measures=all
>
> </div>
>
> </div>
>
> For the unparsed SDMX-JSON response, use `return_raw=True`:
>
> <div id="921413c1" class="cell" data-execution_count="14">
>
> ``` python
> raw = imfp.imf_get(
>     "PCPS", indicator="PCOAL", data_transformation="INDEX", frequency="A",
>     return_raw=True,
> )
> list(raw.keys())
> ```
>
> <div class="cell-output cell-output-display" data-execution_count="11">
>
>     ['meta', 'data']
>
> </div>
>
> </div>
>
> <div id="retries" class="section level1">
>
> # Retries
>
> `max_tries` controls how many times a failed request is retried with exponential backoff. The default is 3:
>
> <div id="7d008711" class="cell" data-execution_count="15">
>
> ``` python
> df = imfp.imf_get("PCPS", indicator="PCOAL", max_tries=5)
> ```
>
> </div>
>
> See [Rate Limits](rate_limits.md) for more on working within the API's limits.
>
> </div>
>
> </div>
>
> </div>
>
> </div>
>
> </div>
>
> </div>
