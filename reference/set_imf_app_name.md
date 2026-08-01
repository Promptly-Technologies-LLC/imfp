## set_imf_app_name()


Set the IMF Application Name.


Usage

``` python
set_imf_app_name(name="imfp")
```


Set a unique application name to be used in requests to the IMF API as an environment variable.


## Parameters


`name: str = ``"imfp"`  
A string representing the application name.


## Returns


`None`  
None


## Raises


`ValueError`  
If the provided name is not a valid string or contains


## Examples

imf_app_name("my_custom_app_name")
