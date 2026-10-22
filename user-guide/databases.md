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


    (225, 7)


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
| 0 | PI_WCA_2026_MAY_VINTAGE | Production Indexes, World and Country Group Ag... | IMF.STA | 2026-05-27T14:17:19.149352Z |
| 1 | FFS | Fossil Fuel Subsidies | IMF.STA | 2026-04-06T16:34:21.566778Z |
| 2 | COFER | Currency Composition of Official Foreign Excha... | IMF.STA | 2025-12-19T16:09:51.115672Z |
| 3 | IL_2026_FEB_VINTAGE | International Liquidity (IL) 2026 February | IMF.STA | 2026-02-25T20:31:17.183284Z |
| 4 | MFS_DC_2026_JAN_VINTAGE | Monetary and Financial Statistics (MFS), Depos... | IMF.STA | 2026-02-09T20:07:05.015110Z |


# Finding the Dataset You Want

Because the result is an ordinary DataFrame, searching it is an ordinary pandas filter. Search the `name` column for a keyword:


``` python
dataflows[dataflows["name"].str.contains("Commodity", case=False, na=False)][
    ["id", "name"]
]
```


|     | id   | name                                  |
|-----|------|---------------------------------------|
| 12  | CTOT | Commodity Terms of Trade (CTOT)       |
| 32  | PCPS | Primary Commodity Price System (PCPS) |


The `description` column often contains terms the title does not, so it is worth searching too:


``` python
matches = dataflows[
    dataflows["description"].str.contains("balance of payments", case=False, na=False)
]
matches[["id", "name"]].head()
```


|     | id                   | name                                              |
|-----|----------------------|---------------------------------------------------|
| 2   | COFER                | Currency Composition of Official Foreign Excha... |
| 28  | BOP_2026_APR_VINTAGE | Balance of Payments (BOP) 2026 April              |
| 81  | ITS                  | International Trade in Services (ITS)             |
| 102 | BOP_AGG              | Balance of Payments and International Investme... |
| 118 | BOP_2026_MAY_VINTAGE | Balance of Payments (BOP) 2026 May                |


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
| 155 | FSI_COUNTRY_METADATA_TABLE_2 | Financial Soundness Indicators (FSI), Country ... | 2026-10-09 22:39:46.289903+00:00 |
| 133 | FAS | Financial Access Survey (FAS) | 2026-10-09 19:09:56.991362+00:00 |
| 72 | AFRREO_2026_APR_VINTAGE | Sub-Saharan Africa Regional Economic Outlook (... | 2026-10-07 19:23:15.996650+00:00 |
| 222 | WEO_2026_APR_VINTAGE | World Economic Outlook (WEO) 2026 April | 2026-10-05 21:05:13.368993+00:00 |
| 79 | CSR | Comprehensive Surveillance Review (CSR) | 2026-10-02 14:31:23.878915+00:00 |


# Reading the Dataflow ID

The `id` column is the value you pass everywhere else:


``` python
pcps = dataflows[dataflows["id"] == "PCPS"]
pcps[["id", "name", "agency", "version"]]
```


|     | id   | name                                  | agency  | version |
|-----|------|---------------------------------------|---------|---------|
| 32  | PCPS | Primary Commodity Price System (PCPS) | IMF.RES | 9.0.0   |


Note the `agency`. Different IMF departments publish through the same API but do not all support the same features -- in particular, only `IMF.STA` currently honors server-side time filtering. [imf_get](../reference/imf_get.md#imfp.imf_get) warns you when you ask for a time window that the publishing agency will ignore. See [Fetching Data](datasets.md#time-filtering).


# Next Step

With a dataflow ID in hand, the next step is finding out how that dataset can be filtered. See [Dimensions and Codes](parameters.md).
