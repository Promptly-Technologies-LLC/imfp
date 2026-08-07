## imf_get_dataflows()


List every dataset published through the IMF Data API.


Usage

``` python
imf_get_dataflows(max_tries=3)
```


This is step 1 of the workflow: use it to find the `dataflow_id` of the dataset you want, then pass that ID to the other functions.


## Parameters


`max_tries: int = ``3`  
Maximum number of requests to attempt. Defaults to 3.


## Returns


`DataFrame`  
pandas.DataFrame: One row per dataflow, with columns `id`, `name`,

`description`, `version`, `agency`, `structure`, and

`last_updated`.


## Raises


`TypeError`  
If max_tries is not an integer.

`ValueError`  
If max_tries is less than 1, or the API returns no dataflows.


## Examples

Find the ID of the Primary Commodity Price System dataset

dataflows = imf_get_dataflows() dataflows\[dataflows\["id"\] == "PCPS"\]
