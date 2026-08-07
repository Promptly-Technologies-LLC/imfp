# Dimensions and Codes


# Why Filtering Matters

Once you have a dataflow ID, you can in principle request the whole dataset:


``` python
import imfp

# Requests all of the Producer Price Index dataset
imfp.imf_get("PPI")
```


This succeeds for a few small datasets and fails for all the large ones, and even when it succeeds it is slow. In practice you almost always want to filter.

Filtering an IMF dataset takes two pieces of information, and `imfp` has one function for each:

- **Which dimensions does this dataset have?** -- [imf_get_datastructure](../reference/imf_get_datastructure.md#imfp.imf_get_datastructure)
- **What values does each dimension accept?** -- [imf_get_codelists](../reference/imf_get_codelists.md#imfp.imf_get_codelists)


# Dimensions

Every dataset is described by a *datastructure definition* (DSD), which lists the **dimensions** the data is broken out by. Each dimension becomes a column in the returned data, and each is categorical: it accepts only a fixed set of values.

Datasets do not share a common set of dimensions. Some use `COUNTRY`, others `REF_AREA`; some spell frequency `FREQUENCY` and others `FREQ`. This is why you have to ask.


``` python
import imfp

dimensions = imfp.imf_get_datastructure("PCPS")
dimensions
```


|     | dimension_id        | type      | position |
|-----|---------------------|-----------|----------|
| 0   | COUNTRY             | Dimension | 0        |
| 1   | INDICATOR           | Dimension | 1        |
| 2   | DATA_TRANSFORMATION | Dimension | 2        |
| 3   | FREQUENCY           | Dimension | 3        |


The columns are:

| Column | Meaning |
|----|----|
| `dimension_id` | The dimension's ID -- what you filter on in [imf_get](../reference/imf_get.md#imfp.imf_get). |
| `type` | `Dimension`, `TimeDimension`, or `Measure`. |
| `position` | The dimension's slot in the dataset's series key. |


## Position

`position` is the dimension's slot in the request the API actually receives. IMF requests are *positional*: filters are sent as a dot-separated key in which each slot corresponds to one dimension, in this order, and an unfiltered slot is a wildcard. [imf_get](../reference/imf_get.md#imfp.imf_get) assembles that key for you, so you never have to think about position -- but it explains why the order of dimensions is fixed and worth glancing at.


## Time and Measures

By default [imf_get_datastructure](../reference/imf_get_datastructure.md#imfp.imf_get_datastructure) lists only the dimensions you can filter on. Time is excluded because you filter it through `start_period`/`end_period` rather than through the key, and measures are excluded because they are outputs rather than filters. Ask for them explicitly if you want to see them:


``` python
imfp.imf_get_datastructure("PCPS", include_time=True, include_measures=True)
```


|     | dimension_id        | type          | position |
|-----|---------------------|---------------|----------|
| 0   | COUNTRY             | Dimension     | 0        |
| 1   | INDICATOR           | Dimension     | 1        |
| 2   | DATA_TRANSFORMATION | Dimension     | 2        |
| 3   | FREQUENCY           | Dimension     | 3        |
| 4   | TIME_PERIOD         | TimeDimension | 4        |
| 5   | OBS_VALUE           | Measure       | \<NA\>   |


Note that the measure has no `position`: it does not occupy a slot in the series key.


# Codes

Knowing that `PCPS` has an `INDICATOR` dimension does not tell you that coal is `PCOAL`. For that, use [imf_get_codelists](../reference/imf_get_codelists.md#imfp.imf_get_codelists), which returns the valid codes for one or more dimensions:


``` python
frequencies = imfp.imf_get_codelists("FREQUENCY", "PCPS")
frequencies[["code", "name"]].head()
```


|     | code | name                  |
|-----|------|-----------------------|
| 0   | A    | Annual                |
| 1   | D    | Daily                 |
| 2   | M    | Monthly               |
| 3   | Q    | Quarterly             |
| 4   | S    | Half-yearly, semester |


The columns are:

| Column | Meaning |
|----|----|
| `dimension_id` | Which dimension the code belongs to. |
| `code` | The value to pass to [imf_get](../reference/imf_get.md#imfp.imf_get). |
| `name` | Short human-readable label. |
| `description` | Longer definition, where the IMF provides one. |
| `codelist_id` | ID of the codelist this came from, e.g. `CL_FREQ`. |
| `codelist_agency` | Agency that maintains the codelist. |
| `codelist_version` | Version of the codelist. |

Dimension IDs are matched case-insensitively, so `"frequency"` and `"FREQUENCY"` both work.


## Fetching Several Dimensions at Once

Pass a list to get everything in one tidy frame -- one row per code, with `dimension_id` telling you which dimension each row belongs to:


``` python
codes = imfp.imf_get_codelists(
    ["INDICATOR", "DATA_TRANSFORMATION", "FREQUENCY"], "PCPS"
)
codes.groupby("dimension_id").size()
```


    dimension_id
    DATA_TRANSFORMATION      4
    FREQUENCY               34
    INDICATOR              136
    dtype: int64


Since it is a single DataFrame, searching it is an ordinary filter:


``` python
codes[
    (codes["dimension_id"] == "INDICATOR")
    & codes["name"].str.contains("Coal", case=False, na=False)
][["code", "name"]]
```


|     | code    | name                                              |
|-----|---------|---------------------------------------------------|
| 14  | PCOAL   | Coal index, Commodity price index, Index, 2016... |
| 15  | PCOALAU | Coal, Australia, US dollars per metric tonne, ... |
| 16  | PCOALSA | Coal, South Africa, US dollars per metric tonn... |


``` python
codes[codes["dimension_id"] == "DATA_TRANSFORMATION"][["code", "name"]]
```


|     | code       | name                                  |
|-----|------------|---------------------------------------|
| 136 | INDEX      | Index                                 |
| 137 | INDEX_PCH  | Index, percent change                 |
| 138 | INDEX_PCHY | Index, percent change from a year ago |
| 139 | USD        | US dollars                            |


To pull every dimension's codes in one call, feed it the datastructure:


``` python
all_codes = imfp.imf_get_codelists(list(dimensions["dimension_id"]), "PCPS")
```


Note that country codelists tend to be large, so this can take a moment.


# Using Codes in a Request

The `code` column holds exactly the values [imf_get](../reference/imf_get.md#imfp.imf_get) expects:


``` python
coal = codes[
    (codes["dimension_id"] == "INDICATOR")
    & (codes["code"] == "PCOAL")
]["code"].tolist()

df = imfp.imf_get(
    "PCPS",
    dimensions={
        "INDICATOR": coal,
        "DATA_TRANSFORMATION": ["INDEX"],
        "FREQUENCY": ["A"],
    },
)
df.head()
```


|     | COUNTRY | INDICATOR | DATA_TRANSFORMATION | FREQUENCY | TIME_PERIOD | OBS_VALUE |
|-----|---------|-----------|---------------------|-----------|-------------|-----------|
| 0   | G001    | PCOAL     | INDEX               | A         | 1992        | 49.892138 |
| 1   | G001    | PCOAL     | INDEX               | A         | 1993        | 43.279151 |
| 2   | G001    | PCOAL     | INDEX               | A         | 1994        | 45.213931 |
| 3   | G001    | PCOAL     | INDEX               | A         | 1995        | 55.433711 |
| 4   | G001    | PCOAL     | INDEX               | A         | 1996        | 53.179458 |


# Labelling Results

Because the codes and the data are both tidy DataFrames keyed on the code, attaching human-readable labels is a merge:


``` python
labelled = df.merge(
    codes[codes["dimension_id"] == "INDICATOR"][["code", "name"]],
    left_on="INDICATOR",
    right_on="code",
    how="left",
).drop(columns=["code"]).rename(columns={"name": "indicator_name"})

labelled[["INDICATOR", "indicator_name", "TIME_PERIOD", "OBS_VALUE"]].head()
```


|  | INDICATOR | indicator_name | TIME_PERIOD | OBS_VALUE |
|----|----|----|----|----|
| 0 | PCOAL | Coal index, Commodity price index, Index, 2016... | 1992 | 49.892138 |
| 1 | PCOAL | Coal index, Commodity price index, Index, 2016... | 1993 | 43.279151 |
| 2 | PCOAL | Coal index, Commodity price index, Index, 2016... | 1994 | 45.213931 |
| 3 | PCOAL | Coal index, Commodity price index, Index, 2016... | 1995 | 55.433711 |
| 4 | PCOAL | Coal index, Commodity price index, Index, 2016... | 1996 | 53.179458 |


# Handling Unknown Dimensions

Asking for a dimension a dataset does not have is an error, and the message tells you what is available:


``` python
try:
    imfp.imf_get_codelists("FREQ", "PCPS")
except ValueError as e:
    print(e)
```


    Unknown dimension(s) for PCPS: FREQ. Available: COUNTRY, DATA_TRANSFORMATION, FREQUENCY, INDICATOR, OBS_VALUE, TIME_PERIOD. Use imf_get_datastructure('PCPS') to list them.


# Next Step

With dimension IDs and codes in hand, you are ready to request data. See [Fetching Data](datasets.md).
