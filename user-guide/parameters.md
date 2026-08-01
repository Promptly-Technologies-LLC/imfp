# Working with Parameters


# Filtering IMF Dataset Requests with Parameters

Once you have a `database_id`, it's possible to make a call to [imf_dataset](../reference/imf_dataset.md#imfp.imf_dataset) to fetch the entire database:


``` python
import imfp
import pandas as pd

# Set float format to 2 decimal places for pandas display output
pd.set_option('display.float_format', lambda x: '%.2f' % x)

# Producer Price Index database
database_id = "PPI"
imfp.imf_dataset(database_id)
```


However, while this will succeed for a few small databases, it will fail for all of the larger ones. And even in the rare case when it succeeds, fetching an entire database can take a long time. You're much better off supplying additional filter parameters to reduce the size of your request.

Requests to databases available through the IMF API are complicated by the fact that each database uses a different set of parameters when making a request. You also have to have the list of valid input codes for each parameter. The [imf_parameters](../reference/imf_parameters.md#imfp.imf_parameters) function solves this problem. Use the function to obtain the full list of parameters and valid input codes for a given database.


# Understanding Filter Parameters

Each database available through the IMF API has its own set of parameters that can be used to filter and specify the data you want to retrieve.

Each parameter will be a column in the data. Each row in the data will contain a value for that parameter. The parameter will always be a categorical variable, meaning that it can take only a limited set of values. We refer to these values as "input codes," because you can input them in your API request to filter the data.

What this means, though, is that before making an API request to retrieve data, you need to know what the available filtering parameters are for the database, and what codes you can use for filtering the data by each parameter.

There are two main functions for working with parameters:

- [imf_parameters()](../reference/imf_parameters.md#imfp.imf_parameters): Get the full list of parameters and valid input codes for a database
- [imf_parameter_defs()](../reference/imf_parameter_defs.md#imfp.imf_parameter_defs): Get text descriptions of what each parameter represents


# Discovering Available Parameters

To get started, you'll need to know what parameters are available for your chosen database. Use [imf_parameters()](../reference/imf_parameters.md#imfp.imf_parameters) to get this information:


``` python
import imfp

# Fetch list of valid parameters for the Producer Price Index database
params = imfp.imf_parameters("PPI")

# View the available parameter names
params.keys()
```


    dict_keys(['country', 'indicator', 'type_of_transformation', 'frequency'])


The function returns a dictionary of data frames.

Each key in the dictionary corresponds to a parameter used in making requests from the database. The value for each key is a data frame with the following columns:

- `input_code`: The valid codes you can use for that parameter
- `description`: A short text description of what each code represents

For example, to see the valid codes for the `frequency` parameter:


``` python
# View the data frame of valid input codes for the frequency parameter
params['frequency']
```


|     | input_code | description           |
|-----|------------|-----------------------|
| 0   | A          | Annual                |
| 1   | D          | Daily                 |
| 2   | M          | Monthly               |
| 3   | Q          | Quarterly             |
| 4   | S          | Half-yearly, semester |
| 5   | W          | Weekly                |
| 6   | A2         | Biennial              |
| 7   | A3         | Triennial             |
| 8   | A4         | Quadrennial           |
| 9   | A5         | Quinquennial          |
| 10  | A10        | Decennial             |
| 11  | A20        | Bidecennial           |
| 12  | A30        | Tridecennial          |
| 13  | A_3        | Three times a year    |
| 14  | M2         | Bimonthly             |
| 15  | M_2        | Semimonthly           |
| 16  | M_3        | Three times a month   |
| 17  | W2         | Biweekly              |
| 18  | W3         | Triweekly             |
| 19  | W4         | Four-weekly           |
| 20  | W_2        | Semiweekly            |
| 21  | W_3        | Three times a week    |
| 22  | D_2        | Twice a day           |
| 23  | H          | Hourly                |
| 24  | H2         | Bihourly              |
| 25  | H3         | Trihourly             |
| 26  | B          | Daily - business week |
| 27  | N          | Minutely              |
| 28  | I          | Irregular             |
| 29  | OA         | Occasional annual     |
| 30  | OM         | Occasional monthly    |
| 31  | \_O        | Other                 |
| 32  | \_U        | Unspecified           |
| 33  | \_Z        | Not applicable        |


# Parameter Definitions

If the parameter name is not self-explanatory, you can use the [imf_parameter_defs()](../reference/imf_parameter_defs.md#imfp.imf_parameter_defs) function to get a text description of what each parameter represents.


``` python
# Get descriptions of what each parameter means
params_defs = imfp.imf_parameter_defs("PPI")

params_defs
```


|  | parameter | description |
|----|----|----|
| 0 | country | Country |
| 1 | indicator | Producer Price Index (PPI) Indicator codelist |
| 2 | type_of_transformation | Producer Price Indexes (PPI) Type of Transform... |
| 3 | frequency | Frequency |


# Supplying Parameters


## Basic Approach (Recommended for Most Users)

To make a request to fetch data from the IMF API, just call [imf_dataset](../reference/imf_dataset.md#imfp.imf_dataset) with the database ID and keyword arguments for each parameter, where the keyword argument name is the parameter name and the value is the list of codes you want.

For instance, on exploring the `frequency` parameter of the Producer Price Index database above, we found that the frequency can take one of three values: "A" for annual, "Q" for quarterly, and "M" for monthly. Thus, to request annual data, we can call [imf_dataset](../reference/imf_dataset.md#imfp.imf_dataset) with `frequency = ["A"]`.

Here's a complete example that fetches annual producer prices from 2000 to 2015:


``` python
# Example: Get annual prices
df = imfp.imf_dataset(
    database_id="PPI",
    frequency=["A"],  # Annual frequency
    indicator=["PPI"],  # Producer Price Index
    start_year=2000,
    end_year=2015
)
```


## Advanced Approaches

For more complex queries, there are two programmatic ways to supply parameters to [imf_dataset](../reference/imf_dataset.md#imfp.imf_dataset). These approaches are particularly useful when you need to filter parameters based on their descriptions or when working with multiple parameter values.


### 1. List Arguments with Parameter Filtering

This approach uses string matching to find the correct parameter codes before passing them to [imf_dataset](../reference/imf_dataset.md#imfp.imf_dataset):


``` python
# Fetch the input code column of the frequency parameter...
selected_frequency = list(
    params['frequency']['input_code'][
        # ...where the description contains "Annual"
        params['frequency']['description'].str.contains("Annual")
    ]
)

# Fetch the input code column of the unit_measure parameter...
selected_type_of_transformation = list(
    params['type_of_transformation']['input_code'][
        # ...where the description contains "Index"
        params['type_of_transformation']['description'].str.contains("Index")
    ]
)

# Request data from the API using the filtered parameter code lists
df = imfp.imf_dataset(
    database_id="PPI",
    frequency=selected_frequency,
    type_of_transformation=selected_type_of_transformation,
    start_year=2000,
    end_year=2015
)

df.head()
```


|     | country | indicator | type_of_transformation | frequency | time_period | obs_value  |
|-----|---------|-----------|------------------------|-----------|-------------|------------|
| 0   | AGO     | WPI       | IX                     | A         | 2008        | 80.099924  |
| 1   | AGO     | WPI       | IX                     | A         | 2009        | 88.676029  |
| 2   | AGO     | WPI       | IX                     | A         | 2010        | 100.000000 |
| 3   | AGO     | WPI       | IX                     | A         | 2011        | 111.889914 |
| 4   | AGO     | WPI       | IX                     | A         | 2012        | 117.840781 |


### 2. Parameters Dictionary Approach

This approach modifies the parameters dictionary directly and passes the entire filtered dictionary to [imf_dataset](../reference/imf_dataset.md#imfp.imf_dataset) as a single `parameters` keyword argument. This is more concise but requires understanding how the parameters dictionary works:


``` python
# Copy the params dictionary
modified_params = params.copy()

# Overwrite the data frame for each parameter in the dictionary with filtered rows
modified_params['frequency'] = params['frequency'][
    # ...where the input code description for frequency contains "Annual"
    params['frequency']['description'].str.contains("Annual")
]
modified_params['type_of_transformation'] = params['type_of_transformation'][
    # ...where the input code description for type_of_transformation contains "Index"
    params['type_of_transformation']['description'].str.contains("Index")
]

# Pass the modified dictionary to imf_dataset
df = imfp.imf_dataset(
    database_id="PPI",
    parameters=modified_params,
    start_year=2000,
    end_year=2015
)

df.head()
```


|     | country | indicator | type_of_transformation | frequency | time_period | obs_value  |
|-----|---------|-----------|------------------------|-----------|-------------|------------|
| 0   | AGO     | WPI       | IX                     | A         | 2008        | 80.099924  |
| 1   | AGO     | WPI       | IX                     | A         | 2009        | 88.676029  |
| 2   | AGO     | WPI       | IX                     | A         | 2010        | 100.000000 |
| 3   | AGO     | WPI       | IX                     | A         | 2011        | 111.889914 |
| 4   | AGO     | WPI       | IX                     | A         | 2012        | 117.840781 |


Note that when using the parameters dictionary approach, you cannot combine it with individual parameter arguments. If you supply a `parameters` argument, any other keyword arguments for individual parameters will be ignored.
