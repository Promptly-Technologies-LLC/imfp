from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from scrapy.crawler import CrawlerProcess
from urllib.parse import urlparse, unquote
import logging
import os
import json
import time
import requests
import traceback
from fake_useragent import UserAgent
from pydantic import BaseModel
from pyshadow.main import Shadow
import urllib.request
import csv
from scraper.logger import Logger


class Scraper:
    executable_path = r'C:\chromedriver.exe'
    options = webdriver.ChromeOptions()
    service = webdriver.chrome.service.Service(executable_path)

    ckan_schema = {
        "url": "",
        "source": "",
        "indicator": "",
        # the above three are added by me
        "additional_data_sources": [{"name": "", "url": ""}],
        "table": "",
        "description": "",
        "tags": [{"name": ""}],
        "limitations": "",
        "concept": "",
        "periodicity": "",
        "topic": "",
        "created": "",
        "last_modified": ""
    }

    def __init__(self, source):
        self.source = source
        self.download_dir = f'Z:\\RawData\\Downloads\\Downloads_{source}'
        self.working_dir = f'Z:\\RawData\\{source}_Data'
        self.logger_dir = f'Z:\\TACFolder\\ScraperLogs\\{source}_logs'
        self.service = webdriver.chrome.service.Service(self.executable_path)
        self.logger = Logger(self.logger_dir)

        # Create the new directories if they do not exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)


    def initialize_driver(self):
        ua = UserAgent()
        self.random_user_agent = ua.random
        self.options = self.get_common_options()
        self.options.add_argument(f'user-agent={self.random_user_agent}')

        self.driver = webdriver.Chrome(service=self.service, options=self.options, service_log_path=os.path.devnull)
        print('initializing chrome driver!')

        if self.random_user_agent:
            print(f'Random user agent: {self.random_user_agent}')
        else:
            print("No user agent found in profile.")

    def get_common_options(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_experimental_option("prefs", {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "download.default_directory": self.download_dir,
            "safebrowsing.enabled": True
        })
        return options



    @staticmethod
    def get_headers(driver):
        # Get the current URL and request headers
        url = driver.current_url
        request_headers = driver.execute_script(
            "return JSON.stringify(window.performance.getEntries()[0].requestHeaders)")

        # Send a GET request to the URL and get the response headers
        response = requests.get(url)
        response_headers = str(response.headers)

        # Print the request and response headers
        print("Request headers:")
        print(request_headers)
        print("Response headers:")
        print(response_headers)

    @staticmethod
    def get_csv_response_into_file(csv_url, target_dir, file_name):
        # Add .csv to file name
        file_name = file_name + '.csv'

        # Download the CSV data from the URL
        response = urllib.request.urlopen(csv_url)
        data = response.read().decode('utf-8')

        # Parse the CSV data using the csv module and write it to a file
        with open(os.path.join(target_dir, file_name), 'w', newline='') as file:
            writer = csv.writer(file)
            rows = csv.reader(data.splitlines())
            header = next(rows)  # Get the header row
            writer.writerow(header)  # Write the header row to the output file
            for row in rows:
                writer.writerow(row)  # Write each data row to the output file

    def clear_cookies(self):
        self.driver.delete_all_cookies()
        print("Cookies cleared.")

    def initialize_driver_actions(self):
        self.actions = ActionChains(self.driver)
        print('initializing chrome driver actions!')

    def initialize_driver_shadow(self):
        self.shadow = Shadow(self.driver)
        print('initializing chrome driver shadow!')

    def close_driver(self):
        print('closing chrome driver!')
        if self.driver:
            self.driver.close()
            self.driver = None

    def quit_driver(self):
        print('closing chrome driver!')
        if self.driver:
            self.driver.quit()
            self.driver = None

    @staticmethod
    def call_spider_crawler(spider_class_name):
        # Create an instance of the spider
        spider = spider_class_name

        # Create a CrawlerProcess object
        process = CrawlerProcess()

        # Start the spider
        process.crawl(spider)

        # Run the spider
        process.start()

    def get_api(self):
        pass

    def scrape(self):
        pass

    def scrape_metadata(self, working_dir, logger):
        pass

    def scrape_data(self, working_dir, logger):
        pass

    @staticmethod
    def manipulate():
        pass

    @staticmethod
    def url_to_title(url):
        # Parse the URL and extract the last part of the path
        path = urlparse(url).path
        last_part = unquote(path.split("/")[-1])

        # Convert the last part to title case and replace hyphens with spaces
        title = last_part.replace("-", " ").capitalize()

        # Return the title
        return title

    @staticmethod
    def check_download_status(download_dir, download_start_wait_time=60):
        recheck = True
        container = 0
        timer = 0
        # check if download has started
        while True:
            if len(os.listdir(download_dir)) > 0:
                print(f"the {download_dir} now contains the file")
                logging.info(f"the {download_dir} now contains the file")
                break
            else:
                time.sleep(1)
                container += 1
            if container == download_start_wait_time:
                print(
                    'file failed to start, Failed - truncated data error or any other error that made the download not start at all therefor no file in download dir')
                logging.info(
                    'file failed to start, Failed - truncated data error or any other error that made the download not start at all therefor no file in download dir')
                container = "fail"
                return container
        # check download time
        while recheck:
            if not os.listdir(download_dir):
                print(
                    'file failed to download, Failed - Network error the downloaded started then failed and the .crdownload file was deleted')
                logging.info(
                    'file failed to download, Failed - Network error the downloaded started then failed and the .crdownload file was deleted')
                timer = "fail"
                return timer
            for file in os.listdir(download_dir):
                if not file.lower().endswith(('.csv', '.xlsx', '.xls', '.xlsm', '.tsv', '.zip')):
                    print(f'Downloading..{timer}')
                    logging.info(f'Downloading..{timer}')
                    time.sleep(1)
                    timer += 1
                if file.lower().endswith(('.csv', '.xlsx', '.xls', '.xlsm', '.tsv', '.zip')):
                    print('Download is done!')
                    logging.info('Download is done!')
                    recheck = False
        # check file size
        file_size = os.path.getsize(os.path.join(download_dir, file))
        file_size_mb = file_size / (1024 * 1024)
        print(f'file size is {file_size_mb} MBs')
        logging.info(f'file size is {file_size_mb} MBs')
        print(f'file name is {file}')
        logging.info(f'file name is {file}')
        if file_size == 0:
            print("file size is 0 bytes, the downloaded file is corrupted")
            logging.info("file size is 0 bytes, the downloaded file is corrupted")
            timer = "fail"
        return timer

    @staticmethod
    def convert_dataset_to_json_dynamically(path, source, source_description, source_url, organization,
                                            trigger_talend: bool):
        # Check if the organization is valid
        if organization not in ["un-agencies", "third-parties"]:
            raise ValueError("Organization must be either 'un-agencies' or 'third-parties'")
        if trigger_talend:
            save_path = ""
        else:
            save_path = r'//10.30.31.77/data_collection_dump/TestData/'
        raw_data = None
        file_metadata = None
        for file in os.listdir(path):
            if 'Metadata' in file and file.endswith('.json'):
                print(file)
                logging.info(file)
                with open(os.path.join(path, file), 'r') as f:
                    file_metadata = json.load(f)
                    continue
            elif 'Metadata' not in file and (file.lower().endswith(('.csv', '.xlsx', '.xls', '.xlsm'))):
                print(file)
                raw_data = file
                continue

        if file_metadata is None or raw_data is None:
            print(f'file_metadata: {file_metadata}')
            logging.info(f'file_metadata: {file_metadata}')
            print(f'raw_data: {raw_data}')
            logging.info(f'raw_data: {raw_data}')
            print('metadata or data or both are none. this dataset will be skipped')
            logging.info('metadata or data or both are none. this dataset will be skipped')
            print('')
            logging.info('')

        new_path = path.replace('Z:', '//10.30.31.77/data_collection_dump')
        new_path2 = new_path.replace("\\", "/")

        BodyDict = {

            "JobPath": f"{new_path2}/{raw_data}",
            "JsonDetails": {
                ## Required
                "organisation": {organization},
                "source": f"{source}",
                "source_description": f"{source_description}",
                "source_url": f"{source_url}",
                "additional_data_sources": [
                    {
                        "name": "",
                        "url": ""  ## this object will be ignored if "name" is empty
                    }
                ],
                "table": file_metadata['table'],
                "description": file_metadata['description'],
                ## Optional
                "JobType": "JSON",
                "CleanPush": True,
                "Server": "str",
                "UseJsonFormatForSQL": False,
                "CleanReplace": True,
                "MergeSchema": False,
                "tags": file_metadata['tags'],
                "limitations": file_metadata['limitations'],
                "concept": file_metadata['concept'],
                "periodicity": file_metadata['periodicity'],
                "topic": file_metadata['topic'],
                "created": file_metadata['created'],
                ## this should follow the following formats %Y-%m-%dT%H:%M:%S" or "%Y-%m-%d"
                "last_modified": file_metadata['last_modified'],
                ## this should follow the following formats %Y-%m-%dT%H:%M:%S" or "%Y-%m-%d"
                # False to not trigger talend True to trigger talend after conversion
                "TriggerTalend": trigger_talend,
                # real
                "SavePathForJsonOutput": save_path

            }

        }

        print(BodyDict['JobPath'])
        logging.info(BodyDict['JobPath'])
        # print('')
        print('now triggering hassan api')
        logging.info('now triggering hassan api')
        # trigger hassan api for talend
        TriggerInferSchemaToJsonAPIClass = TriggerInferSchemaToJsonAPI(BodyDict=BodyDict)
        TriggerInferSchemaToJsonAPIClass.TriggerAPI()
        print('trigerred hassan api successfully')
        logging.info('trigerred hassan api successfully')

    @staticmethod
    def convert_scraped_data(path, source, source_description, source_url, organization, trigger_talend: bool):
        # Check if the organization is valid
        if organization not in ["un-agencies", "third-parties"]:
            raise ValueError("Organization must be either 'un-agencies' or 'third-parties'")
        if trigger_talend:
            save_path = ""
        else:
            save_path = r'//10.30.31.77/data_collection_dump/TestData/'
        l = []
        c = 0
        for x in os.listdir(path):
            l.append(x)
        for i in range(len(l)):
            # print(l[i])
            current_dir = os.path.join(path, l[i])
            raw_data = None
            file_metadata = None
            if os.path.isdir(current_dir):
                print(current_dir)
                for file in os.listdir(current_dir):
                    # print(file)
                    if 'Metadata' in file and file.endswith('.json'):
                        print(file)
                        logging.info(file)
                        with open(os.path.join(current_dir, file), 'r') as f:
                            file_metadata = json.load(f)
                            continue
                    elif 'Metadata' not in file and (file.lower().endswith(('.csv', '.xlsx', '.xls', '.xlsm'))):
                        print(file)
                        logging.info(file)
                        raw_data = file
                        continue
                    # else:
                    #     # no metadata (empty dict)
                    #     file_metadata = {}
                # time.sleep(1)
                # if os.path.isdir(current_dir):
                #     print(current_dir)
                # else:
                #     print(f'{current_dir} is not a path')
                # for file in os.listdir(current_dir):
                #     if 'Metadata' not in file and (
                #             file.endswith('.csv') or file.endswith('.xlsx') or file.endswith('.xls')):
                #         print(file)
                #         logging.info(file)
                #         raw_data = file
                #         break

            if file_metadata is None or raw_data is None:
                print(f'file_metadata: {file_metadata}')
                logging.info(f'file_metadata: {file_metadata}')
                print(f'raw_data: {raw_data}')
                logging.info(f'raw_data: {raw_data}')
                print('metadata or data or both are none. this dataset will be skipped')
                logging.info('metadata or data or both are none. this dataset will be skipped')
                print('')
                logging.info('')
                continue

            new_path = current_dir.replace('Z:', '//10.30.31.77/data_collection_dump')
            new_path2 = new_path.replace("\\", "/")

            BodyDict = {

                "JobPath": f"{new_path2}/{raw_data}",
                "JsonDetails": {
                    ## Required
                    "organisation": f"{organization}",
                    "source": f"{source}",
                    "source_description": f"{source_description}",
                    "source_url": f"{source_url}",
                    "additional_data_sources": file_metadata['additional_data_sources'],
                    "table": file_metadata['table'],
                    "description": file_metadata['description'],
                    ## Optional
                    "JobType": "JSON",
                    "CleanPush": True,
                    "Server": "str",
                    "UseJsonFormatForSQL": False,
                    "CleanReplace": True,
                    "MergeSchema": False,
                    "tags": file_metadata['tags'],
                    "limitations": file_metadata['limitations'],
                    "concept": file_metadata['concept'],
                    "periodicity": file_metadata['periodicity'],
                    "topic": file_metadata['topic'],
                    "created": file_metadata['created'],
                    ## this should follow the following formats %Y-%m-%dT%H:%M:%S" or "%Y-%m-%d"
                    "last_modified": file_metadata['last_modified'],
                    ## this should follow the following formats %Y-%m-%dT%H:%M:%S" or "%Y-%m-%d"
                    # False to not trigger talend True to trigger talend after conversion
                    "TriggerTalend": trigger_talend,
                    "SavePathForJsonOutput": save_path

                }

            }

            print(BodyDict['JobPath'])
            logging.info(BodyDict['JobPath'])
            # print('')
            print('now triggering hassan api')
            logging.info('now triggering hassan api')
            # trigger hassan api for talend
            TriggerInferSchemaToJsonAPIClass = TriggerInferSchemaToJsonAPI(BodyDict=BodyDict)
            TriggerInferSchemaToJsonAPIClass.TriggerAPI()
            print('trigerred hassan api successfully')
            logging.info('trigerred hassan api successfully')
            c += 1
            print('')
            logging.info('')
        return c


class TriggerInferSchemaToJsonAPI:
    def __init__(self, BodyDict):
        self.URL = "http://10.30.31.77:8010/InferSchemaAndConvertToJson"

        ## Verify Input
        class TagsClass(BaseModel):
            name: str = "Unclassified"

        class AdditionalSources(BaseModel):
            url: str = ""
            name: str = ""

        class JsonDetailsModel(BaseModel):
            ## For Delta
            JobType: str = "JSON"
            CleanPush: bool = True
            Server: str = "str"
            UseJsonFormatForSQL: bool = False
            CleanReplace: bool = True
            MergeSchema: bool = False
            ## For Both Metadata
            tags: list[TagsClass] = [TagsClass()]
            organisation: str
            source: str
            source_description: str
            source_url: str
            additional_data_sources: list[AdditionalSources] = [AdditionalSources()]
            table: str
            description: str
            limitations: str = ""
            concept: str = ""
            periodicity: str = ""
            topic: str = ""
            created: str = ""
            last_modified: str = ""
            TriggerTalend: bool = True
            SavePathForJsonOutput: str = ""

        class InferSchemaToJsonJOB(BaseModel):
            JobPath: str
            JsonDetails: JsonDetailsModel

        InferSchemaToJsonJOB(**BodyDict)

        self.BodyDict = BodyDict

    def TriggerAPI(self):
        JsonBody = self.BodyDict
        try:
            Response = requests.post(url=self.URL, json=JsonBody)
            if not Response.ok:
                ErrorReponse = f"Failed to Connect to Infer Schema with Status Code {Response.status_code} and error {Response.text}"
                raise ConnectionRefusedError(ErrorReponse)
            ResponseDict = Response.json()

        except Exception as e:
            LogMessage = f"\nFailed To Connect To Infer Schema and Save To Json API due to this error: {traceback.format_exc()}"
            # print(LogMessage)
            raise ConnectionError(LogMessage)


class RequestRunJobTalend:
    def __init__(self):
        self.URL = "http://10.30.31.77:8020/talendjob"

    def TriggerTalendckanJob(self):
        JsonBody = {
            "JobType": "ckan"
        }
        i = 1
        Maxi = 5
        while i <= Maxi:
            try:
                Response = requests.post(url=self.URL, json=JsonBody)
                ResponseDict = Response.json()
                break
            except Exception as e:
                LogMessage = f"{i}: Failed To Connect To Talend Wrapper API due to this error: {traceback.format_exc()}"
                print(LogMessage)
            i = i + 1

    def TriggerTalenddeltaJob(self):
        JsonBody = {
            "JobType": "delta"
        }
        i = 1
        Maxi = 5
        while i <= Maxi:
            try:
                Response = requests.post(self.URL, json=JsonBody)
                ResponseDict = Response.json()
                break
            except Exception as e:
                LogMessage = f"{i}: Failed To Connect To Talend Wrapper API due to this error: {traceback.format_exc()}"
                print(LogMessage)
            i = i + 1

    def TriggerBothJobs(self):
        JsonBody = {
            "JobType": "both"
        }
        i = 1
        Maxi = 5
        while i <= Maxi:
            try:
                Response = requests.post(self.URL, json=JsonBody)
                ResponseDict = Response.json()
                break
            except Exception as e:
                LogMessage = f"{i}: Failed To Connect To Talend Wrapper API due to this error: {traceback.format_exc()}"
                print(LogMessage)
            i = i + 1
        print('triggered talend')
#
# if __name__ == "__main__":
#     RequestRunJobTalendClass = RequestRunJobTalend()
#     #RequestRunJobTalendClass.TriggerTalendckanJob()
#     RequestRunJobTalendClass.TriggerTalenddeltaJob()
