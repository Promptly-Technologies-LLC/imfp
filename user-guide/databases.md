# Discovering Datasets


# Dataflows

The IMF publishes hundreds of separate datasets through its API. In SDMX -- the standard the API speaks -- a dataset is called a **dataflow**, and every request has to name one. So before you can fetch any data, you need to:

1.  Get the list of available dataflows
2.  Find the ID of the one you want

That ID is the first argument to every other function in `imfp`.


# Listing Dataflows

[imf_get_dataflows](../reference/imf_get_dataflows.md#imfp.imf_get_dataflows) returns the full catalogue as a tidy DataFrame:


``` python
import imfp

dataflows = imfp.imf_get_dataflows()
dataflows.shape
```


    (222, 7)


Each row describes one dataset:

| Column | Meaning |
|----|----|
| `id` | The dataflow ID, e.g. `PCPS`. This is what you pass to the other functions. |
| `name` | Human-readable title. |
| `description` | Longer prose description, where the IMF provides one. |
| `version` | Version of the dataflow definition. |
| `agency` | The IMF department that publishes it, e.g. `IMF.STA`. |
| `structure` | URN of the datastructure definition that backs it. |
| `last_updated` | When the dataset was last refreshed. |


``` python
dataflows[["id", "name", "agency", "last_updated"]].head()
```


|  | id | name | agency | last_updated |
|----|----|----|----|----|
| 0 | IIPCC_2026_APR_VINTAGE | Currency Composition of the International Inve... | IMF.STA | 2026-04-27T15:03:17.665208Z |
| 1 | ANEA | National Economic Accounts (NEA), Annual Data | IMF.STA | 2025-03-28T08:00:46.650082Z |
| 2 | GFS_COFOG | GFS Government Expenditures by Function | IMF.STA | 2025-06-06T01:34:26.584454Z |
| 3 | MFS_FMP_2026_MAY_VINTAGE | Monetary and Financial Statistics (MFS), Finan... | IMF.STA | 2026-05-27T14:59:17.737322Z |
| 4 | LS_2026_FEB_VINTAGE | Labor Statistics (LS) 2026 February | IMF.STA | 2026-02-25T20:34:44.315994Z |


# Finding the Dataset You Want

Because the result is an ordinary DataFrame, searching it is an ordinary pandas filter. Search the `name` column for a keyword:


``` python
dataflows[dataflows["name"].str.contains("Commodity", case=False, na=False)][
    ["id", "name"]
]
```


|     | id   | name                                  |
|-----|------|---------------------------------------|
| 85  | CTOT | Commodity Terms of Trade (CTOT)       |
| 211 | PCPS | Primary Commodity Price System (PCPS) |


The `description` column often contains terms the title does not, so it is worth searching too:


``` python
matches = dataflows[
    dataflows["description"].str.contains("balance of payments", case=False, na=False)
]
matches[["id", "name"]].head()
```


|     | id                   | name                                              |
|-----|----------------------|---------------------------------------------------|
| 42  | IL                   | International Liquidity (IL)                      |
| 55  | BOP_2026_FEB_VINTAGE | Balance of Payments (BOP) 2026 February           |
| 78  | COFER                | Currency Composition of Official Foreign Excha... |
| 123 | BOP                  | Balance of Payments (BOP)                         |
| 143 | BOP_AGG              | Balance of Payments and International Investme... |


# Checking How Current a Dataset Is

`last_updated` tells you when each dataset was last refreshed, which is useful when you are deciding whether a series is current enough for your purposes:


``` python
import pandas as pd

recent = dataflows.dropna(subset=["last_updated"]).copy()
recent["last_updated"] = pd.to_datetime(recent["last_updated"], format="mixed")
recent.sort_values("last_updated", ascending=False)[["id", "name", "last_updated"]].head()
```


|  | id | name | last_updated |
|----|----|----|----|
| 214 | IRFCL | International Reserves and Foreign Currency Li... | 2026-06-19 15:17:41.650334+00:00 |
| 11 | ISORA_LATEST_DATA_PUB | ISORA Latest Data | 2026-06-15 17:13:23.041621+00:00 |
| 99 | GPT | IMF Global Policy Tracker: How Countries are R... | 2026-06-12 16:15:44.521971+00:00 |
| 19 | FM | Fiscal Monitor (FM) | 2026-06-03 16:00:56.895956+00:00 |
| 111 | MFS_OFC_2026_MAY_VINTAGE | Monetary and Financial Statistics (MFS), Other... | 2026-05-27 15:19:21.834692+00:00 |


# Reading the Dataflow ID

The `id` column is the value you pass everywhere else:


``` python
pcps = dataflows[dataflows["id"] == "PCPS"]
pcps[["id", "name", "agency", "version"]]
```


|     | id   | name                                  | agency  | version |
|-----|------|---------------------------------------|---------|---------|
| 211 | PCPS | Primary Commodity Price System (PCPS) | IMF.RES | 9.0.0   |


Note the `agency`. Different IMF departments publish through the same API but do not all support the same features -- in particular, only `IMF.STA` currently honors server-side time filtering. [imf_get](../reference/imf_get.md#imfp.imf_get) warns you when you ask for a time window that the publishing agency will ignore. See [Fetching Data](datasets.md#time-filtering).


# Next Step

With a dataflow ID in hand, the next step is finding out how that dataset can be filtered. See [Dimensions and Codes](parameters.md).
