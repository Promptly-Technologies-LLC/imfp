import time

from scraper.data_cleaner import DataCleaner
from scraper.logger import Logger
from scraper.ckan_schema import *
import imfp
import tempfile
import webbrowser
from IPython.display import display
from requests import RequestException


# https://github.com/chriscarrollsmith/imfp
class ImfpManipulator(DataCleaner):
    working_dir = r'Z:\RawData\IMF_Data'
    logger_dir = R'Z:\TACFolder\ScraperLogs'
    logger_name = r"IMFP"

    def __init__(self):
        # Create the new directories if they do not exist
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        # Initialize the Logger class
        self.logger = Logger(os.path.join(self.logger_dir, self.logger_name))

    @staticmethod
    def view_all_databases_in_browser(df=imfp.imf_databases()):
        html = df.to_html()
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
            url = 'file://' + f.name
            f.write(html)
        webbrowser.open(url)

    @staticmethod
    def set_imf_app_name(my_custom_app_name: str):
        # Set custom app name as an environment variable
        imfp.set_imf_app_name(my_custom_app_name)

    @staticmethod
    def fetch_imf_databases():
        databases = imfp.imf_databases()
        return databases

    @staticmethod
    def fetch_full_datasets_of_db_id_with_indicators(database_id, database_index, valid_param_elements,
                                                     sub_working_dir):
        print(f"'indicator' key is valid! with length: {len(valid_param_elements)}")
        print(f'getting the dataset of every indicator inside {database_index}: {database_id}')
        for indicator in valid_param_elements["input_code"]:
            print(f'getting dataset for: {indicator} inside {database_index}: {database_id}')
            while True:
                try:
                    df = imfp.imf_dataset(database_id=database_id, indicator=indicator)
                    print(f'got the dataset for indicator: {indicator}')
                    df.to_excel(fr"{sub_working_dir}\{database_id}_{database_index}_{indicator}.xlsx",
                                sheet_name=f'{indicator[:31]}',
                                index=False)
                    print(f'Creating excel file for: {indicator}')
                    break
                except RequestException as e:
                    print(
                        f'RequestException inside fetch_full_datasets_of_db_id_with_indicators: {type(e).__name__} - {e.args}')
                    print('Sleeping for 15 minutes then retrying...')
                    time.sleep(900)
                except ValueError as e:
                    print(
                        f'ValueError inside fetch_full_datasets_of_db_id_with_indicators: {type(e).__name__} - {e.args}')
                    print("An error occurred when downloading", indicator, ": ", e)
                    break
            print('')
        print(f"Retrieved every 'indicator' dataset available inside {database_index}: {database_id}")

    @staticmethod
    def fetch_full_datasets_of_db_id_with_commodities(database_id, database_index, valid_param_elements,
                                                      sub_working_dir):
        print(f"'commodity' key is valid! with length: {len(valid_param_elements)}")
        print(f'getting the dataset of every commodity inside {database_index}: {database_id}')
        for commodity in valid_param_elements["input_code"]:
            print(f'getting dataset for: {commodity} inside {database_index}: {database_id}')
            while True:
                try:
                    df = imfp.imf_dataset(database_id=database_id, commodity=commodity)
                    print(f'got the dataset for commodity: {commodity}')
                    df.to_excel(fr"{sub_working_dir}\{database_id}_{database_index}_{commodity}.xlsx",
                                sheet_name=f'{commodity[:31]}',
                                index=False)
                    print(f'Creating excel file for: {commodity}')
                    break
                except RequestException as e:
                    print(
                        f'RequestException inside fetch_full_datasets_of_db_id_with_commodities: {type(e).__name__} - {e.args}')
                    print('Sleeping for 15 minutes then retrying...')
                    time.sleep(900)
                except ValueError as e:
                    print(
                        f'ValueError inside fetch_full_datasets_of_db_id_with_commodities: {type(e).__name__} - {e.args}')
                    print("An error occurred when downloading", commodity, ": ", e)
                    break
            print('')
        print(f"Retrieved every 'commodity' dataset available inside {database_index}: {database_id}")

    @staticmethod
    def fetch_full_datasets_of_db_id_with_classifications(database_id, database_index, valid_param_elements,
                                                          sub_working_dir):
        print(f"'classification' key is valid! with length: {len(valid_param_elements)}")
        print(f'getting the dataset of every classification inside {database_index}: {database_id}')
        for classification in valid_param_elements["input_code"]:
            print(f'getting dataset for: {classification} inside {database_index}: {database_id}')
            while True:
                try:
                    df = imfp.imf_dataset(database_id=database_id, classification=classification)
                    print(f'got the dataset for classification: {classification}')
                    df.to_excel(fr"{sub_working_dir}\{database_id}_{database_index}_{classification}.xlsx",
                                sheet_name=f'{classification[:31]}',
                                index=False)
                    print(f'Creating excel file for: {classification}')
                    break
                except RequestException as e:
                    print(
                        f'RequestException inside fetch_full_datasets_of_db_id_with_classifications: {type(e).__name__} - {e.args}')
                    print('Sleeping for 15 minutes then retrying...')
                    time.sleep(900)
                except ValueError as e:
                    print(
                        f'ValueError inside fetch_full_datasets_of_db_id_with_classifications: {type(e).__name__} - {e.args}')
                    print("An error occurred when downloading", classification, ": ", e)
                    break
            print('')
        print(f"Retrieved every 'classification' dataset available inside {database_index}: {database_id}")

    @staticmethod
    def fetch_full_datasets_of_db_id_with_instrument_and_assets_classifications(database_id,
                                                                                database_index,
                                                                                valid_param_elements,
                                                                                second_valid_param_elements,
                                                                                sub_working_dir):
        print(f"'instrument_and_assets_classification' key is valid! with length: {len(valid_param_elements)}")
        print(f"'gfs_sto' key is valid! with length: {len(second_valid_param_elements)}")
        print(
            f"now will loop every 'instrument_and_assets_classification' over all elements of 'gfs_sto' in favor to get back data")
        print(
            f'getting the dataset of every instrument_and_assets_classification inside {database_index}: {database_id}')
        for instrument_and_assets_classification in valid_param_elements["input_code"]:
            for gfs_sto in second_valid_param_elements["input_code"]:
                print(
                    f'getting dataset for: {instrument_and_assets_classification} with {gfs_sto} inside {database_index}: {database_id}')
                while True:
                    try:
                        df = imfp.imf_dataset(database_id=database_id,
                                              instrument_and_assets_classification=instrument_and_assets_classification,
                                              gfs_sto=gfs_sto)
                        print(
                            f'got the dataset for instrument_and_assets_classification: {instrument_and_assets_classification} with {gfs_sto}')
                        df.to_excel(
                            fr"{sub_working_dir}\{database_id}_{database_index}_{instrument_and_assets_classification}_{gfs_sto}.xlsx",
                            sheet_name=f'{instrument_and_assets_classification[:31]}',
                            index=False)
                        print(f'Creating excel file for: {instrument_and_assets_classification} with {gfs_sto}')
                        break
                    except RequestException as e:
                        print(
                            f'RequestException inside fetch_full_datasets_of_db_id_with_instrument_and_assets_classifications: {type(e).__name__} - {e.args}')
                        print('Sleeping for 15 minutes then retrying...')
                        time.sleep(900)
                    except ValueError as e:
                        print(
                            f'ValueError inside fetch_full_datasets_of_db_id_with_instrument_and_assets_classifications: {type(e).__name__} - {e.args}')
                        print(f"An error occurred when downloading {instrument_and_assets_classification} with {gfs_sto} : {e}")
                        break
                print('')
        print(
            f"Retrieved every 'instrument_and_assets_classification' with 'gfs_sto' dataset available inside {database_index}: {database_id}")

    @staticmethod
    def check_database_id_valid_parameter(database_id):
        # check if 'indicator' parameter exists for this database_id
        indicator = 'indicator'
        commodity = 'commodity'
        classification = 'classification'
        # if instrument_and_assets_classification is valid i need to iterate them over gfs_sto values too
        gfs_sto = 'gfs_sto'
        instrument_and_assets_classification = 'instrument_and_assets_classification'
        try:
            print(f"checking if 'indicator' key is valid for: {database_id}")
            indicators = imfp.imf_parameters(database_id)[indicator]
            print(f"'indicator' key is valid for: {database_id}")
            return indicator, indicators, None, None
        except KeyError:
            print("invalid 'indicator' key")
            # check if 'commodity' parameter exists for this database_id
            try:
                print(f"checking if 'commodity' key is valid for: {database_id}")
                commodities = imfp.imf_parameters(database_id)[commodity]
                print(f"'commodity' key is valid for: {database_id}")
                return commodity, commodities, None, None
            except KeyError:
                print("invalid 'commodity' key")
                # check if 'classification' parameter exists for this database_id
                try:
                    print(f"checking if 'classification' key is valid for: {database_id}")
                    classifications = imfp.imf_parameters(database_id)[classification]
                    print(f"'classification' key is valid for: {database_id}")
                    return classification, classifications, None, None
                except KeyError:
                    print("invalid 'classification' key")
                    try:
                        print(f"checking if 'instrument_and_assets_classification' key is valid for: {database_id}")
                        instrument_and_assets_classifications = imfp.imf_parameters(database_id)[
                            instrument_and_assets_classification]
                        print(f"'instrument_and_assets_classification' key is valid for: {database_id}")
                        print(
                            f"since 'instrument_and_assets_classification' is valid i have to also find and loop with 'gfs_sto' to make the filter work")
                        gfs_stos = imfp.imf_parameters(database_id)[
                            gfs_sto]
                        return instrument_and_assets_classification, instrument_and_assets_classifications, gfs_sto, gfs_stos
                    except KeyError:
                        print("invalid 'instrument_and_assets_classification' key")
                        print('bruh')

    def sort_databases_by_indicator_or_commodity(self):
        _imf_wait_time = 10
        ImfpManipulator.set_imf_app_name('unescwa')
        # Iterate over all available databases
        for database_id, description, index, total in ImfpManipulator.yield_database_info():
            if index < 10:
                print(f'skipping: {index}')
                continue
            # Defective databases
            if database_id in ['DOT_2020Q1', 'TBG_USD', 'FAS_2015', 'GFS01', 'FM202010', 'APDREO202010', 'AFRREO202010',
                               'WHDREO202010', 'BOPAGG_2020']:
                print(
                    f'skipping {database_id}: one of the nine databases that do not exist but are listed (bug from the imf source)')
                print('')
                continue
            # Create sub dir for this database_id
            print(f"Processing database {index} of {total}: {database_id}: {description}")
            sub_working_dir = self.create_sub_folder(working_dir=self.working_dir, folder_name=f'{database_id}_{index}')
            # Create respective metadata
            print(f'Creating metadata for this {index}: {database_id}')
            file_name_metadata = f"Metadata_{database_id}_{index}.json"
            ckan_instance = CKANSchema(
                url="https://github.com/chriscarrollsmith/imfp",
                source="IMF RESTful JSON API",
                indicator=f"{database_id}",
                table=f"{description}",
                description=f"{description}",
                concept=r"https://datahelp.imf.org/knowledgebase/topics/69743-methodology",

            )
            save_to_json(ckan_instance, file_name_metadata, sub_working_dir)
            time.sleep(1)
            # Check the valid param
            print(f"Checking which valid parameter exists for {index}: {database_id}")
            while True:
                try:
                    valid_param, valid_param_elements, second_valid_param, second_valid_param_elements = self.check_database_id_valid_parameter(
                        database_id)
                    break
                except ValueError as e:
                    print(f'ValueError for check_database_id_valid_parameter: {type(e).__name__} - {e.args}')
                    time.sleep(1)
            if valid_param == 'indicator':
                self.fetch_full_datasets_of_db_id_with_indicators(database_id=database_id,
                                                                  valid_param_elements=valid_param_elements,
                                                                  database_index=index,
                                                                  sub_working_dir=sub_working_dir)
            elif valid_param == 'commodity':
                self.fetch_full_datasets_of_db_id_with_commodities(database_id=database_id,
                                                                   valid_param_elements=valid_param_elements,
                                                                   database_index=index,
                                                                   sub_working_dir=sub_working_dir)
            elif valid_param == 'classification':
                self.fetch_full_datasets_of_db_id_with_classifications(database_id=database_id,
                                                                       valid_param_elements=valid_param_elements,
                                                                       database_index=index,
                                                                       sub_working_dir=sub_working_dir)
            elif valid_param == 'instrument_and_assets_classification' and second_valid_param == 'gfs_sto':
                self.fetch_full_datasets_of_db_id_with_instrument_and_assets_classifications(database_id=database_id,
                                                                                             valid_param_elements=valid_param_elements,
                                                                                             second_valid_param_elements=second_valid_param_elements,
                                                                                             database_index=index,
                                                                                             sub_working_dir=sub_working_dir)
            else:
                print('bruh')
            # Combine the Excel files into one big xlsx or csv file after getting all the datasets of the database
            print(f'Now will combine excel files of {index}: {database_id}')
            self.combine_excel_files_into_one(folder_path=sub_working_dir)
            time.sleep(1)

    @staticmethod
    def fetch_database_description(database_id: str):
        df = ImfpManipulator.fetch_imf_databases()  # call the function that returns the DataFrame
        # filter the DataFrame to get the row with the given database_id and retrieve the description
        description = df.loc[df["database_id"] == database_id, "description"].iloc[0]
        print(description)
        return description

    @staticmethod
    def fetch_database_id_based_on_description(keyword: str):
        df = ImfpManipulator.fetch_imf_databases()  # call the function that returns the DataFrame
        # filter the DataFrame to get the row with the given database_id and retrieve the description
        ids = df[df['description'].str.contains(keyword)]
        print(ids)
        return ids

    @staticmethod
    def fetch_first_five_database_dataset_rows(database_id: str):
        # Request Data from the API
        df = imfp.imf_dataset(database_id=database_id)

        # Display the first few entries in the retrieved data frame
        display(df.head())

    @staticmethod
    def fetch_list_of_valid_parameters(database_id: str):
        print(f'List of valid parameters for database_id: {database_id}')
        params = imfp.imf_parameters(database_id)
        print(params.keys())
        return params

    @staticmethod
    def fetch_list_of_valid_parameters_with_definition(database_id: str):
        print(f'List of valid parameters with their definition for database_id: {database_id}')
        params_def = imfp.imf_parameter_defs(database_id)
        print(params_def)
        return params_def

    @staticmethod
    def view_input_codes_and_description_of_database_valid_parameters(database_id: str):
        params = ImfpManipulator.fetch_list_of_valid_parameters(database_id)
        for param in params:
            input_codes = params[param]
            print(input_codes)

    @staticmethod
    def yield_database_info():
        while True:
            try:
                df = ImfpManipulator.fetch_imf_databases()
                break
            except ValueError as e:
                print(f'ValueError inside yield_database_info: {type(e).__name__} - {e.args}')
                print('Sleeping for 15 minutes then retrying...')
                time.sleep(900)

        num_databases = len(df)
        for index, row in df.iterrows():
            yield row['database_id'], row['description'], index, num_databases - 1
