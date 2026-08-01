# Suggestions for Usage


# Determining Data Availability

The only way to be certain whether data is available for a given set of parameters is to make a request to the API and see if it succeeds. If you get an empty data frame, try a less restrictive version of your request.


# Working with Large Data Frames


## Inspecting Data

`imfp` outputs data in `pandas` DataFrames, so you will want to use the `pandas` package for its functions for viewing and manipulating this object type.

For large datasets, you can use the `pandas` library's `info()` method to get a quick summary of the data frame, including the number of rows and columns, the count of non-missing values, the column names, and the data types.


``` python
import imfp
import pandas as pd

# Set float format to 2 decimal places for pandas display output
pd.set_option('display.float_format', lambda x: '%.2f' % x)

df: pd.DataFrame = imfp.imf_dataset(
    database_id="PCPS",
    indicator=["PCOAL"],
    data_transformation=["IX"]
)

# Quick summary of DataFrame
df.info()
```


    /home/runner/work/imfp/imfp/imfp/data.py:582: UserWarning: ['IX'] not valid value(s) for data_transformation and will be ignored. Use imf_parameters('PCPS') to get valid parameters.
      warn(


    <class 'pandas.core.frame.DataFrame'>
    RangeIndex: 1758 entries, 0 to 1757
    Data columns (total 6 columns):
     #   Column               Non-Null Count  Dtype  
    ---  ------               --------------  -----  
     0   country              1758 non-null   object 
     1   indicator            1758 non-null   object 
     2   data_transformation  1758 non-null   object 
     3   frequency            1758 non-null   object 
     4   time_period          1758 non-null   object 
     5   obs_value            1758 non-null   float64
    dtypes: float64(1), object(5)
    memory usage: 82.5+ KB


Alternatively, you can use the `head()` method to view the first 5 rows of the data frame.


``` python
# View first 5 rows of DataFrame
df.head()
```


|     | country | indicator | data_transformation | frequency | time_period | obs_value |
|-----|---------|-----------|---------------------|-----------|-------------|-----------|
| 0   | G001    | PCOAL     | INDEX               | A         | 1992        | 49.89     |
| 1   | G001    | PCOAL     | INDEX               | A         | 1993        | 43.28     |
| 2   | G001    | PCOAL     | INDEX               | A         | 1994        | 45.21     |
| 3   | G001    | PCOAL     | INDEX               | A         | 1995        | 55.43     |
| 4   | G001    | PCOAL     | INDEX               | A         | 1996        | 53.18     |


## Cleaning Data


### Numeric Conversion

All data is returned from the IMF API as a text (object) data type, so you will want to cast numeric columns to numeric.


``` python
# Numeric columns
numeric_cols = ["obs_value"]

# Cast numeric columns
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
```


### Categorical Conversion

You can also convert string columns to categorical types for better memory usage.


``` python
# Convert categorical columns like ref_area and indicator to category type
categorical_cols = [
  "frequency",
  "country",
  "indicator"
]

df[categorical_cols] = df[categorical_cols].astype("category")
```


### NA Removal

After conversion, you may want to drop any rows with missing values.


``` python
# Drop rows with missing values
df = df.dropna()
```


### Time Period Conversion

The `time_period` column can be more difficult to work with, because it may be differently formatted depending on the frequency of the data.

Annual data will be formatted as a four-digit year, such as "2000", which can be trivially converted to numeric.

However, quarterly data will be formatted as "2000-Q1", monthly data will be formatted like "2000-M01", etc.

You can use the `pandas` library's `to_datetime()` method with the `format="mixed"` argument to convert this column to a datetime object in a format-agnostic way:


``` python
# Convert time_period to datetime
df["datetime"] = pd.to_datetime(df["time_period"], format="mixed")
df[["frequency", "datetime"]].head()
```


|     | frequency | datetime   |
|-----|-----------|------------|
| 0   | A         | 1992-01-01 |
| 1   | A         | 1993-01-01 |
| 2   | A         | 1994-01-01 |
| 3   | A         | 1995-01-01 |
| 4   | A         | 1996-01-01 |


Alternatively, you can split the `time_period` column into separate columns for year, quarter, and month, and then convert each to a numeric value:


``` python
# Split time_period into separate columns
df["year"] = df["time_period"].str.extract(r"(\d{4})")[0]
df["quarter"] = df["time_period"].str.extract(r"[Q](\d{1})")[0]
df["month"] = df["time_period"].str.extract(r"[M](\d{2})")[0]

# Convert year, quarter, and month to numeric
df["year"] = pd.to_numeric(df["year"])
df["quarter"] = pd.to_numeric(df["quarter"])
df["month"] = pd.to_numeric(df["month"])

# Return head for non-na months
df[["time_period", "year", "quarter", "month"]].dropna(subset=["month"]).head()
```


|     | time_period | year | quarter | month |
|-----|-------------|------|---------|-------|
| 34  | 1992-M01    | 1992 | NaN     | 1.00  |
| 35  | 1992-M02    | 1992 | NaN     | 2.00  |
| 36  | 1992-M03    | 1992 | NaN     | 3.00  |
| 37  | 1992-M04    | 1992 | NaN     | 4.00  |
| 38  | 1992-M05    | 1992 | NaN     | 5.00  |


## Summarizing Data

After converting columns to numeric, you can use the `describe()` function to get a quick summary of the statistical properties of these, including the count of rows, the mean, the standard deviation, the minimum and maximum values, and the quartiles.


``` python
# Statistical summary
df.describe()
```


|       | obs_value | datetime                      | year    | quarter | month   |
|-------|-----------|-------------------------------|---------|---------|---------|
| count | 1758.00   | 1758                          | 1758.00 | 414.00  | 1242.00 |
| mean  | 42.12     | 2008-10-29 00:36:56.165529088 | 2008.74 | 2.49    | 6.46    |
| min   | -69.21    | 1992-01-01 00:00:00           | 1992.00 | 1.00    | 1.00    |
| 25%   | -3.92     | 2000-01-01 00:00:09           | 2000.00 | 1.00    | 3.00    |
| 50%   | 9.24      | 2009-01-01 00:00:02.500000    | 2009.00 | 2.00    | 6.00    |
| 75%   | 66.03     | 2017-04-01 00:00:00           | 2017.00 | 3.00    | 9.00    |
| max   | 577.58    | 2026-04-01 00:00:00           | 2026.00 | 4.00    | 12.00   |
| std   | 77.29     | NaN                           | 9.96    | 1.12    | 3.45    |


## Viewing Data

For large data frames, it can be useful to view the data in a browser window. To facilitate this, you can define a `View()` function as follows. This function will save the data frame to a temporary HTML file and open it in your default web browser.


``` python
import tempfile
import webbrowser

# Define a simple function to view data frame in a browser window
def View(df: pd.DataFrame):
    html = df.to_html()
    with tempfile.NamedTemporaryFile('w', 
    delete=False, suffix='.html') as f:
        url = 'file://' + f.name
        f.write(html)
    webbrowser.open(url)

# Call the function
View(df)
```


# Common Data Transformations

The World Economic Outlook (WEO) and Consumer Price Index (CPI) databases provide key macroeconomic aggregates that are frequently needed when working with other IMF datasets. Here, we'll demonstrate how to use three fundamental indicators--GDP, price deflators, and population statistics--to transform your data.

These transformations are essential for:

- Converting nominal to real dollar values
- Calculating per capita metrics
- Harmonizing data across different frequencies
- Adjusting for different unit scales

For a complete, end-to-end example of these transformations in a real analysis workflow, see Jenny Xu's superb [demo notebook](https://github.com/jennyxu/imfp-demo).


## Fetching Adjusters

First, let's retrieve the key adjustment variables:


``` python
# Fetch GDP Deflator (Index, Quarterly)
deflator = imfp.imf_dataset(
    database_id="QNEA",
    indicator="B1GQ",
    price_type="PD",  # Price deflator
    type_of_transformation="IX",  # Index
    frequency="Q",
    start_year=2010
)

# Fetch Population Estimates (Annual)
population = imfp.imf_dataset(
    database_id="WEO",
    indicator="LP",
    frequency="A",
    start_year=2010
)

# Fetch Exchange Rate (Quarterly)
exchange_rate = imfp.imf_dataset(
    database_id="ER", 
    indicator="XDC_USD",  # Domestic currency per USD
    frequency="Q",
    start_year=2010
)
```


    /home/runner/work/imfp/imfp/imfp/data.py:748: UserWarning: Agency IMF.RES does not support time filters; time window will be ignored.
      warn(


We'll also retrieve a nominal GDP series to be adjusted:


``` python
# Fetch Nominal GDP (Domestic currency, annual)
nominal_gdp = imfp.imf_dataset(
    database_id="ANEA",
    indicator="B1GQ",
    price_type="V",  # Current prices
    type_of_transformation="XDC",  # Domestic currency
    frequency="A",
    start_year=2010
)
```


**Key Indicators**:

- **QNEA** (Quarterly National Economic Accounts): `B1GQ` with `price_type="PD"` and `type_of_transformation="IX"` for GDP deflator index
- **WEO** (World Economic Outlook): `LP` for population estimates
- **ER** (Exchange Rates): `XDC_USD` for exchange rate (domestic currency per USD)
- **ANEA** (Annual National Economic Accounts): `B1GQ` with `price_type="V"` and `type_of_transformation="XDC"` for nominal GDP in domestic currency

> **Note: Database Changes**
>
> The IMF has updated their API structure. The former IFS (International Financial Statistics) database, which provided a central point of access to these adjusters, has been discontinued and replaced with more specialized databases:
>
> - **ANEA/QNEA**: National Economic Accounts data (annual and quarterly)
> - **WEO**: World Economic Outlook data including population
> - **ER**: Exchange rate data
> - **CPI**: Consumer Price Index data
> - **MFS_CBS**: Monetary and Financial Statistics, Central Bank data
>
> Use [imf_databases()](../reference/imf_databases.md#imfp.imf_databases) to see all available databases and `imf_parameters(database_id)` to explore their indicators.


## Alternative: Using CPI for Price Adjustments

If you prefer to use the Consumer Price Index instead of the GDP deflator:


``` python
# Fetch CPI (All Items, Index)
cpi = imfp.imf_dataset(
    database_id="CPI",
    index_type="CPI",
    coicop_1999="_T",  # All Items
    type_of_transformation="IX",  # Index
    frequency="Q",
    start_year=2010
)
```


## Harmonizing Frequencies

When working with data of different frequencies, you'll often need to harmonize them. For example, population and national GDP are available at an annual frequency, while the GDP deflator and exchange rates can only be obtained at a monthly or quarterly frequency. There are two common approaches:

1.  Using Q4 values: This approach is often used for stock variables (measurements taken at a point in time) and when you want to align with end-of-year values:


``` python
# Keep only Q4 observations for annual comparisons
deflator = deflator[deflator['time_period'].str.contains("Q4")]
exchange_rate = exchange_rate[exchange_rate['time_period'].str.contains("Q4")]

# Extract just the year from the time period for Q4 data
deflator['time_period'] = deflator['time_period'].str[:4]
exchange_rate['time_period'] = exchange_rate['time_period'].str[:4]
```


2.  Calculating annual averages: This approach is more appropriate for flow variables (measurements over a period) and when you want to smooth out seasonal variations:


``` python
# Alternative: Calculate annual averages
deflator = deflator.groupby(
    ['country', deflator['time_period']], 
    as_index=False
).agg({
    'obs_value': 'mean'
})
```


Choose the appropriate method based on your specific analysis needs and the economic meaning of your variables.


## Merging Datasets

We can combine the datasets using `pd.DataFrame.merge()` with `country` and `time_period` as keys:


``` python
merged = (
    nominal_gdp.merge(
        deflator,
        on=['country', 'time_period'],
        suffixes=('_gdp', '_deflator')
    )
    .merge(
        population,
        on=['country', 'time_period']
    )
    .merge(
        exchange_rate,
        on=['country', 'time_period'],
        suffixes=('_population', '_exchange_rate')
    )
)
```


## Calculating Real Values

With the merged dataset, we can now calculate real GDP and per capita values:


``` python
# Convert nominal to real GDP
merged['real_gdp'] = (
    (merged['obs_value_gdp'] / merged['obs_value_deflator']) * 100
)

# Calculate per capita values (using population obs_value)
merged['real_gdp_per_capita'] = merged['real_gdp'] / merged['obs_value_population']

# Display the first 5 rows of the transformed data
merged[['country', 'time_period', 'real_gdp', 'real_gdp_per_capita']].head()
```


|     | country | time_period | real_gdp         | real_gdp_per_capita |
|-----|---------|-------------|------------------|---------------------|
| 0   | ALB     | 2011        | 1266392354394.82 | 435906.15           |
| 1   | ALB     | 2011        | 1266392354394.82 | 435906.15           |
| 2   | ALB     | 2012        | 1302994927918.21 | 449246.48           |
| 3   | ALB     | 2012        | 1302994927918.21 | 449246.48           |
| 4   | ALB     | 2013        | 1327471211207.68 | 458524.71           |


## Exchange Rate Adjustment

Note that this result is still in the domestic currency of the country. If you need to convert to a common currency, you can use the exchange rate data from the ER (Exchange Rates) database.


``` python
# Because 'obs_value_exchange_rate' is local-currency-per-USD,
# dividing local-currency real GDP by it yields GDP in USD.
merged["real_gdp_usd"] = (
    merged["real_gdp"] / merged["obs_value_exchange_rate"]
)

# (Optional) real GDP per capita in USD
merged["real_gdp_usd_per_capita"] = (
    merged["real_gdp_usd"] / merged["obs_value_population"]
)

# Inspect results
merged[["time_period","country","real_gdp","real_gdp_usd","real_gdp_usd_per_capita"]].head()
```


|  | time_period | country | real_gdp | real_gdp_usd | real_gdp_usd_per_capita |
|----|----|----|----|----|----|
| 0 | 2011 | ALB | 1266392354394.82 | 11776012222.38 | 4053.43 |
| 1 | 2011 | ALB | 1266392354394.82 | 12190133681.53 | 4195.98 |
| 2 | 2012 | ALB | 1302994927918.21 | 12309824543.39 | 4244.18 |
| 3 | 2012 | ALB | 1302994927918.21 | 12088272826.03 | 4167.79 |
| 4 | 2013 | ALB | 1327471211207.68 | 13032311125.15 | 4501.52 |
