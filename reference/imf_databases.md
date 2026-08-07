## imf_databases()


List IMF database IDs and descriptions


Usage

``` python
imf_databases(times=3)
```


> **Warning: Deprecated since version 2.0.0**
>
> Use [imfp.imf_get_dataflows()](imf_get_dataflows.md#imfp.imf_get_dataflows) instead. This function will be removed in imfp 3.0.0.

Returns a DataFrame with database_id and text description for each database available through the IMF API endpoint.


times : int, optional, default 3 Maximum number of API requests to attempt.


pandas.DataFrame DataFrame containing database_id and description columns.


Return first 6 IMF database IDs and descriptions

databases = imf_databases()
