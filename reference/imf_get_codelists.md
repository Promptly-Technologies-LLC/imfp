## imf_get_codelists()


Look up the valid codes for one or more of a dataset's dimensions.


Usage

``` python
imf_get_codelists(
    dimension_ids,
    dataflow_id,
    max_tries=3,
)
```


This is step 3 of the workflow: the `code` column holds the values to pass to [imf_get()](imf_get.md#imfp.imf_get).


## Parameters


`dimension_ids: str or list`  
One or more dimension IDs from imf_get_datastructure(). Matching is case-insensitive.

`dataflow_id: str`  
A dataflow ID from imf_get_dataflows().

`max_tries: int = ``3`  
Maximum number of requests to attempt. Defaults to 3.


## Returns


`DataFrame`  
pandas.DataFrame: One row per code, with columns `dimension_id`,

`code`, `name`, `description`, `codelist_id`,

`codelist_agency`, and `codelist_version`. Dimensions that are not

enumerated (they accept free-form values) contribute no rows.


## Raises


`TypeError`  
If an argument has the wrong type.

`ValueError`  
If no dimension is named, if max_tries is less than 1, or if the dataflow does not exist or lacks a requested dimension.


## Examples

Find the commodity indicator codes for PCPS

imf_get_codelists("COMMODITY", "PCPS")

Fetch two dimensions at once

imf_get_codelists(\["COMMODITY", "FREQ"\], "PCPS")
