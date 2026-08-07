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
| 0 | MFS_DC_2026_MAY_VINTAGE | Monetary and Financial Statistics (MFS), Depos... | IMF.STA | 2026-05-27T14:51:58.879098Z |
| 1 | MCDREO | Middle East and Central Asia Regional Economic... | IMF.MCD | 2025-10-16T00:20:10.062512Z |
| 2 | WHDREO_2025_OCT_VINTAGE | Western Hemisphere Regional Economic Outlook (... | IMF.WHD | 2026-04-13T17:42:08.662531Z |
| 3 | PCPS | Primary Commodity Price System (PCPS) | IMF.RES | 2025-06-16T17:59:44.643694Z |
| 4 | MFS_DC | Monetary and Financial Statistics (MFS), Depos... | IMF.STA | 2025-11-27T16:58:36.728552Z |


# Finding the Dataset You Want

Because the result is an ordinary DataFrame, searching it is an ordinary pandas filter. Search the `name` column for a keyword:


``` python
dataflows[dataflows["name"].str.contains("Commodity", case=False, na=False)][
    ["id", "name"]
]
```


|     | id   | name                                  |
|-----|------|---------------------------------------|
| 3   | PCPS | Primary Commodity Price System (PCPS) |
| 114 | CTOT | Commodity Terms of Trade (CTOT)       |


The `description` column often contains terms the title does not, so it is worth searching too:


``` python
matches = dataflows[
    dataflows["description"].str.contains("balance of payments", case=False, na=False)
]
matches[["id", "name"]].head()
```


|     | id                   | name                                              |
|-----|----------------------|---------------------------------------------------|
| 10  | BOP                  | Balance of Payments (BOP)                         |
| 41  | COFER                | Currency Composition of Official Foreign Excha... |
| 73  | BOP_2026_FEB_VINTAGE | Balance of Payments (BOP) 2026 February           |
| 128 | IL                   | International Liquidity (IL)                      |
| 173 | ITS                  | International Trade in Services (ITS)             |


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
| 206 | IRFCL | International Reserves and Foreign Currency Li... | 2026-06-19 15:17:41.650334+00:00 |
| 122 | ISORA_LATEST_DATA_PUB | ISORA Latest Data | 2026-06-15 17:13:23.041621+00:00 |
| 44 | GPT | IMF Global Policy Tracker: How Countries are R... | 2026-06-12 16:15:44.521971+00:00 |
| 220 | FM | Fiscal Monitor (FM) | 2026-06-03 16:00:56.895956+00:00 |
| 7 | MFS_OFC_2026_MAY_VINTAGE | Monetary and Financial Statistics (MFS), Other... | 2026-05-27 15:19:21.834692+00:00 |


# Reading the Dataflow ID

The `id` column is the value you pass everywhere else:


``` python
pcps = dataflows[dataflows["id"] == "PCPS"]
pcps[["id", "name", "agency", "version"]]
```


|     | id   | name                                  | agency  | version |
|-----|------|---------------------------------------|---------|---------|
| 3   | PCPS | Primary Commodity Price System (PCPS) | IMF.RES | 9.0.0   |


Note the `agency`. Different IMF departments publish through the same API but do not all support the same features -- in particular, only `IMF.STA` currently honors server-side time filtering. [imf_get](../reference/imf_get.md#imfp.imf_get) warns you when you ask for a time window that the publishing agency will ignore. See [Fetching Data](datasets.md#time-filtering).


# Next Step

With a dataflow ID in hand, the next step is finding out how that dataset can be filtered. See [Dimensions and Codes](parameters.md).
