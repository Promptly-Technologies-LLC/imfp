# Working with Databases


# Understanding IMF Databases

The IMF serves many different databases through its API, and the API needs to know which of these many databases you're requesting data from. Before you can fetch any data, you'll need to:

1.  Get a list of available databases
2.  Find the database ID for the data you want

Then you can use that database ID to fetch the data.


# Fetching the Database List


## Fetching an Index of Databases with the [imf_databases](../reference/imf_databases.md#imfp.imf_databases) Function

To obtain the list of available databases and their corresponding IDs, use [imf_databases](../reference/imf_databases.md#imfp.imf_databases):


``` python
import imfp

#Fetch the list of databases available through the IMF API
databases = imfp.imf_databases()
databases.head()
```


|  | database_id | description |
|----|----|----|
| 0 | ITS | International Trade in Services (ITS) |
| 1 | PI_WCA | Production Indexes, World and Country Group Ag... |
| 2 | QGFS_2026_APR_VINTAGE | Quarterly Government Finance Statistics (QGFS)... |
| 3 | EER_2026_JAN_VINTAGE | Effective Exchange Rates (ER) 2026 January |
| 4 | UNFCCC | Greenhouse Gas Emissions (UNFCCC) |


This function returns the IMF's listing of 71 databases available through the API.


# Exploring the Database List

To view and explore the database list, it's possible to explore subsets of the data frame by row number with `databases.loc`:


``` python
# View a subset consisting of rows 5 through 9
databases.loc[5:9]
```


|  | database_id | description |
|----|----|----|
| 5 | GS_ED | Gender Statistics (GS) Education |
| 6 | BOP_2026_JAN_VINTAGE | Balance of Payments (BOP) 2026 January |
| 7 | SDG | IMF Reported SDG Data |
| 8 | QGFS_2026_FEB_VINTAGE | Quarterly Government Finance Statistics (QGFS)... |
| 9 | MFS_OFC | Monetary and Financial Statistics (MFS), Other... |


Or, if you already know which database you want, you can fetch the corresponding code by searching for a string match using `str.contains` and subsetting the data frame for matching rows. For instance, here's how to search for commodities data:


``` python
databases[databases['description'].str.contains("Commodity")]
```


|     | database_id | description                           |
|-----|-------------|---------------------------------------|
| 99  | CTOT        | Commodity Terms of Trade (CTOT)       |
| 178 | PCPS        | Primary Commodity Price System (PCPS) |


See also [Working with Large Data Frames](usage.md#working-with-large-data-frames) for sample code showing how to view the full contents of the data frame in a browser window.


# Best Practices

1.  **Cache the Database List**: The database list rarely changes. Consider saving it locally if you'll be making multiple queries. See [Caching Strategy](rate_limits.md#caching-strategy) for sample code.

2.  **Search Strategically**: Use specific search terms to find relevant databases. For example:

    - "Price" for price indices
    - "Trade" for trade statistics
    - "Financial" for financial data

3.  **Use a Browser Viewer**: See [Working with Large Data Frames](usage.md#working-with-large-data-frames) for sample code showing how to view the full contents of the data frame in a browser window.

4.  **Note Database IDs**: Once you find a database you'll use frequently, note its database ID for future reference.


# Next Steps

Once you've identified the database you want to use, you'll need to:

1.  Get the list of parameters for that database (see [Parameters](parameters.md))
2.  Use those parameters to fetch your data (see [Datasets](datasets.md))
