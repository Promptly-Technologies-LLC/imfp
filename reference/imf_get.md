## imf_get()


Fetch observations from an IMF dataset.


Usage

``` python
imf_get(dataflow_id: str, dimensions: dict[str, Any] | None = None, start_period: int | str | None = None, end_period: int | str | None = None, max_tries: int = 3, print_url: bool = False, return_raw: Literal[False] = False, kwargs: Any = {}) -> DataFrame
 
imf_get(dataflow_id: str, dimensions: dict[str, Any] | None = None, start_period: int | str | None = None, end_period: int | str | None = None, max_tries: int = 3, print_url: bool = False, return_raw: Literal[True] = True, kwargs: Any = {}) -> dict[str, Any]
```


This is step 4 of the workflow. Dimensions you do not filter on are wildcarded, so omitting `dimensions` entirely requests the whole dataset -- which for most datasets is slow and very large.

Codes are not validated before the request is sent; the API is the authority on what is valid. Use [imf_get_codelists()](imf_get_codelists.md#imfp.imf_get_codelists) to find valid codes.


## Parameters


`dataflow_id: str`  
A dataflow ID from imf_get_dataflows().

`dimensions: dict = None`  
Maps dimension IDs to the code or list of codes to include. Dimension IDs are matched case-insensitively.

`start_period: int or str = None`  
Earliest period to return, as a year ("2015"), quarter ("2015-Q1"), or month ("2015-01").

`end_period: int or str = None`  
Latest period to return, in the same formats as start_period.

`max_tries: int = ``3`  
Maximum number of requests to attempt. Defaults to 3.

`print_url: bool = ``False`  
Whether to print the request URL, which is useful when reporting a problem with a specific query.

`return_raw: bool = ``False`  
Whether to return the parsed JSON response as a dict instead of a DataFrame.

`**kwargs: Any`  
Dimension filters given as keyword arguments, e.g. `freq="A"`. Equivalent to passing them in `dimensions`.


## Returns


`DataFrame | dict[str, Any]`  
pandas.DataFrame: One row per observation, with a column per series

dimension (named as in the datastructure), plus `TIME_PERIOD` and

`OBS_VALUE`. Returns an empty DataFrame, and warns, when the query

matches no observations. If return_raw is True, returns the raw parsed

JSON dict instead.


## Raises


`TypeError`  
If an argument has the wrong type, including a dimension given something other than a code string or list of them.

`ValueError`  
If max_tries is less than 1, if the same dimension is supplied twice, or if the dataflow does not exist or lacks a named dimension.


## Examples

Annual coal prices, 2000-2015

imf_get( "PCPS", dimensions={"COMMODITY": "PCOAL", "FREQ": "A"}, start_period=2000, end_period=2015, )

The same query using keyword arguments

imf_get("PCPS", commodity="PCOAL", freq="A", start_period=2000)
