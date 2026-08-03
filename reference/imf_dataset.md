## imf_dataset()


Download a data series from the IMF.


Usage

``` python
imf_dataset(database_id: str, parameters: dict[str, DataFrame] | None = None, start_year: int | str | None = None, end_year: int | str | None = None, return_raw: Literal[False] = False, print_url: bool = False, times: int = 3, include_metadata: Literal[False] = False, kwargs: DimensionFilter = {}) -> DataFrame
 
imf_dataset(database_id: str, parameters: dict[str, DataFrame] | None = None, start_year: int | str | None = None, end_year: int | str | None = None, return_raw: Literal[False] = False, print_url: bool = False, times: int = 3, include_metadata: Literal[True] = True, kwargs: DimensionFilter = {}) -> tuple[dict[str, Any], DataFrame]
 
imf_dataset(database_id: str, parameters: dict[str, DataFrame] | None = None, start_year: int | str | None = None, end_year: int | str | None = None, return_raw: Literal[True] = True, print_url: bool = False, times: int = 3, include_metadata: Literal[False] = False, kwargs: DimensionFilter = {}) -> dict[str, Any]
 
imf_dataset(database_id: str, parameters: dict[str, DataFrame] | None = None, start_year: int | str | None = None, end_year: int | str | None = None, return_raw: Literal[True] = True, print_url: bool = False, times: int = 3, include_metadata: Literal[True] = True, kwargs: DimensionFilter = {}) -> tuple[dict[str, Any], dict[str, Any]]
```


## Parameters


`database_id: str`  
Database ID for the database from which you would like to request data. Can be found using imf_databases().

`parameters: dict = None`  
Dictionary of data frames providing input parameters for your API request. Retrieve dictionary of all possible input parameters using imf_parameters() and filter each data frame in the dictionary to reduce it to the inputs you want.

`start_year: int = None`  
Four-digit year. Earliest year for which you would like to request data.

`end_year: int = None`  
Four-digit year. Latest year for which you would like to request data.

`return_raw: bool = ``False`  
Whether to return the raw list returned by the API instead of a cleaned-up data frame.

`print_url: bool = ``False`  
Whether to print the URL used in the API call.

`times: int = ``3`  
Maximum number of requests to attempt.

`include_metadata: bool = ``False`  
Whether to return the database metadata header along with the data series.

`**kwargs: DimensionFilter`  
Dimension filters as keyword arguments. Each value must be a code string or a list of code strings. Use imf_parameters() to identify which parameters to use for requests from a given database and to see all valid input codes for each parameter.


## Returns


`DataFrame | dict[str, Any] | tuple[dict[str, Any], DataFrame | dict[str, Any]]`  
If return_raw == False and include_metadata == False, returns a pandas

DataFrame with the data series. If return_raw == False but

include_metadata == True, returns a tuple whose first item is the

database header, and whose second item is the pandas DataFrame. If

return_raw == True, returns the raw JSON fetched from the API endpoint.
