## imf_parameter_defs()


Get text descriptions of input parameters used in making API


Usage

``` python
imf_parameter_defs(
    database_id,
    times=3,
    inputs_only=True,
)
```


requests from a given IMF database


database_id : str A database_id from imf_databases(). times : int, optional, default 3 Maximum number of API requests to attempt. inputs_only : bool, optional, default False Whether to return only parameters used as inputs in API requests, or also output variables.


pandas.DataFrame A DataFrame of input parameters used in making API requests from a given IMF database, along with text descriptions or definitions of those parameters. Useful in cases when parameter names returned by imf_databases() are not self-explanatory. (Note that the usefulness of text descriptions can be uneven, depending on the database design.)


Get names and text descriptions of parameters used in IMF API calls to

the Primary Commodity Price System database

param_defs = imf_parameter_defs(database_id='PCPS')
