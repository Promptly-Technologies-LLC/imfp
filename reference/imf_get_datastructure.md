## imf_get_datastructure()


List the dimensions a dataset can be filtered on.


Usage

``` python
imf_get_datastructure(
    dataflow_id, max_tries=3, include_time=False, include_measures=False
)
```


This is step 2 of the workflow. The returned `position` is the dimension's slot in the dataset's series key, which is why the order matters: a request that filters on some dimensions and wildcards others still has to line them up positionally. [imf_get()](imf_get.md#imfp.imf_get) handles that for you.


## Parameters


`dataflow_id: str`  
A dataflow ID from imf_get_dataflows().

`max_tries: int = ``3`  
Maximum number of requests to attempt. Defaults to 3.

`include_time: bool = ``False`  
Whether to also list the time dimension. Time is filtered through start_period/end_period rather than through the series key, so it is excluded by default.

`include_measures: bool = ``False`  
Whether to also list measures (the observation values). Measures are outputs, not filters, so they are excluded by default.


## Returns


`DataFrame`  
pandas.DataFrame: One row per component, with columns `dimension_id`,

`type`, and `position`.


## Raises


`TypeError`  
If an argument has the wrong type.

`ValueError`  
If max_tries is less than 1, or the dataflow does not exist or defines no dimensions.


## Examples

See what the Primary Commodity Price System can be filtered on

imf_get_datastructure("PCPS")
