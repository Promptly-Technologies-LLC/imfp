# API Reference


## Fetching Data


The econdataverse-style workflow: discover a dataset, inspect how it can be filtered, look up valid codes, then request observations.


[imf_get_dataflows()](imf_get_dataflows.md#imfp.imf_get_dataflows)  
List every dataset published through the IMF Data API.

[imf_get_datastructure()](imf_get_datastructure.md#imfp.imf_get_datastructure)  
List the dimensions a dataset can be filtered on.

[imf_get_codelists()](imf_get_codelists.md#imfp.imf_get_codelists)  
Look up the valid codes for one or more of a dataset's dimensions.

[imf_get()](imf_get.md#imfp.imf_get)  
Fetch observations from an IMF dataset.


## Configuration


Settings that affect how requests are made


[set_imf_app_name()](set_imf_app_name.md#imfp.set_imf_app_name)  
Set the IMF Application Name.

[set_imf_wait_time()](set_imf_wait_time.md#imfp.set_imf_wait_time)  
Set the IMF wait time as an environment variable.


## Deprecated


The pre-2.0 interface. These still work but emit a DeprecationWarning and will be removed in imfp 3.0.0. See the migration guide.


[imf_databases()](imf_databases.md#imfp.imf_databases)  
List IMF database IDs and descriptions

[imf_parameters()](imf_parameters.md#imfp.imf_parameters)  
List input parameters and available parameter values for use in

[imf_parameter_defs()](imf_parameter_defs.md#imfp.imf_parameter_defs)  
Get text descriptions of input parameters used in making API

[imf_dataset()](imf_dataset.md#imfp.imf_dataset)  
Download a data series from the IMF.
