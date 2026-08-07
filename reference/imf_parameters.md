## imf_parameters()


List input parameters and available parameter values for use in


Usage

``` python
imf_parameters(
    database_id,
    times=2,
)
```


making API requests from a given IMF database.

> **Warning: Deprecated since version 2.0.0**
>
> Use [imfp.imf_get_codelists()](imf_get_codelists.md#imfp.imf_get_codelists) instead, which returns a single tidy DataFrame rather than a dict of DataFrames. This function will be removed in imfp 3.0.0.


database_id : str A database_id from imf_databases(). times : int, optional, default 3 Maximum number of API requests to attempt.


dict A dictionary of DataFrames, where each key corresponds to an input parameter for API requests from the database. All values are DataFrames with an 'input_code' column and a 'description' column. The 'input_code' column is a character list of all possible input codes for that parameter when making requests from the IMF API endpoint. The 'descriptions' column is a character list of text descriptions of what each input code represents.


Fetch the full list of indicator codes and descriptions for the Primary

Commodity Price System database

params = imf_parameters(database_id='PCPS')
