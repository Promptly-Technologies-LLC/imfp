# Requesting Datasets


# Making a Request

To retrieve data from an IMF database, you'll need the database ID and any relevant [filter parameters](parameters.md). Here's a basic example using the Producer Price Index (PPI) database from 2000 to 2015:


``` python
import imfp

# Get parameters and their valid codes
params = imfp.imf_parameters("PPI")

# Fetch annual coal price index data
df = imfp.imf_dataset(
    database_id="PPI",
    frequency=["A"],  # Annual frequency
    indicator=["WPI"],  # Wholesale Price Index
    type_of_transformation=["IX"],
    start_year=2000,
    end_year=2015
)
```


This example creates two objects we'll use in the following sections:

- `params`: A dictionary of parameters and their valid codes
- `df`: The retrieved data frame containing our requested data


# Decoding Returned Data

When you retrieve data using [imf_dataset](../reference/imf_dataset.md#imfp.imf_dataset), the returned data frame contains columns that correspond to the parameters you specified in your request. However, these columns use input codes (short identifiers) rather than human-readable descriptions. To make your data more interpretable, you can replace these codes with their corresponding text descriptions using the parameter information from [imf_parameters](../reference/imf_parameters.md#imfp.imf_parameters), so that codes like "A" (Annual) or "W00" (World) become self-explanatory labels.

For example, suppose we want to decode the `frequency`, `country`, and `type_of_transformation` (unit) columns in our dataset. We'll merge the parameter descriptions into our data frame:


``` python
# Decode frequency codes (e.g., "A" → "Annual")
decoded_df = df.merge(
    # Select code-description pairs
    params['frequency'][['input_code', 'description']],
    # Match codes in the data frame
    left_on='frequency',
    # ...to codes in the parameter data
    right_on='input_code',
    # Keep all data rows
    how='left'
).drop(columns=['frequency', 'input_code']
).rename(columns={"description": "frequency"})

# Decode geographic area codes (e.g., "W00" → "World")
decoded_df = decoded_df.merge(
    params['country'][['input_code', 'description']],
    left_on='country',
    right_on='input_code',
    how='left'
).drop(columns=['country', 'input_code']
).rename(columns={"description":"country"})

# Decode unit codes (e.g., "IX" → "Index")
decoded_df = decoded_df.merge(
    params['type_of_transformation'][['input_code', 'description']],
    left_on='type_of_transformation',
    right_on='input_code',
    how='left'
).drop(columns=['type_of_transformation', 'input_code']
).rename(columns={"description":"type_of_transformation"})

decoded_df.head()
```


|     | indicator | time_period | obs_value  | frequency | country | type_of_transformation |
|-----|-----------|-------------|------------|-----------|---------|------------------------|
| 0   | WPI       | 2008        | 80.099924  | Annual    | Angola  | Index                  |
| 1   | WPI       | 2009        | 88.676029  | Annual    | Angola  | Index                  |
| 2   | WPI       | 2010        | 100.000000 | Annual    | Angola  | Index                  |
| 3   | WPI       | 2011        | 111.889914 | Annual    | Angola  | Index                  |
| 4   | WPI       | 2012        | 117.840781 | Annual    | Angola  | Index                  |


After decoding, the data frame is much more human-interpretable. This transformation makes the data more accessible for analysis and presentation, while maintaining all the original information.
