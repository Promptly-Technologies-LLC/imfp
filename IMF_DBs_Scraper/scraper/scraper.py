import httpx
from selectolax.parser import HTMLParser
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
import logging
import os
import json
import shutil
import time
import zipfile
import gzip
import pandas as pd
from zipfile import BadZipFile
from pandas.errors import EmptyDataError
import win32com.client as win32
import requests
import traceback
from pydantic import BaseModel


# =CONCATENATE("""", A1, """, ")
# local machine profile_path = r'C:\Users\10229953\AppData\Roaming\Mozilla\Firefox\Profiles\bx2zaeff.Patrick'
# remote machine profile_path = r'C:\Users\system_int\AppData\Roaming\Mozilla\Firefox\Profiles\ys8frds0.Patrick'

class Scraper:
    download_dir = r'Z:\RawData\Downloads'
    working_dir = r'Z:\RawData'

    def __init__(self, machine):
        assert machine in ['local', 'remote'], f"Error: machine must be 'local' or 'remote', got {machine}"
        self.machine = machine
        self.options = Options()
        # self.options.add_argument('--headless')
        self.options.add_argument("USER AGENT")
        self.options.add_argument(fr"-profile {self.machine}")
        self.options = webdriver.FirefoxOptions()
        self.options.binary_location = 'C:\\Program Files\\Mozilla Firefox\\firefox.exe'
        self.options.set_preference("browser.download.folderList", 2)
        self.options.set_preference("browser.download.manager.showWhenStarting", False)
        self.options.set_preference("browser.download.dir", self.download_dir)
        # service: meaning geckodriver path and no geckodriver logs
        self.service = FirefoxService(r'C:\geckodriver.exe', log_path=os.path.devnull)
        self.driver = webdriver.Firefox(service=self.service, options=self.options)

    @staticmethod
    def logger(project_name):
        path = r'Z:\TACFolder\ScraperLogs'
        project_name_logs = project_name + '.log'
        if not os.path.exists(os.path.join(path, project_name)):
            os.makedirs(os.path.join(path, project_name))
        logging.basicConfig(level=logging.INFO, filename=os.path.join(path, project_name, project_name_logs),
                            filemode='a',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def get_html(self):
        page = httpx.get(self.url)
        return page.content

    def get_data(self):
        html = HTMLParser(self.get_html())
        return html
        # scraper = Scraper("https://www.example.com")
        # data = scraper.get_data()
        # print(data.text())

    def scrape(self, working_dir, logger):
        pass

    @staticmethod
    def manipulate():
        pass

    def close(self):
        print('closing driver!')
        self.driver.close()

    @staticmethod
    def convert_tsv_to_csv(tsv_file_path):
        ext = '.tsv'
        os.chdir(tsv_file_path)
        for file in os.listdir(tsv_file_path):
            if file.endswith(ext):
                # read the .tsv file into a dataframe
                df = pd.read_csv(file, sep="\t")
                # write the dataframe to a .csv file
                df.to_csv(f"{file}.csv", index=False)
        os.chdir('../UNDP_Data')
        print(f'{file} converted from .tsv to .csv successfully!')

    @staticmethod
    def convert_csv_to_xlsx(csv_file, output_path, xlsx_file_name):
        # reading the csv file
        csv_df = pd.read_csv(csv_file)
        # creating an output excel file
        result_xlsx = pd.ExcelWriter(os.path.join(output_path, xlsx_file_name))
        # converting the csv file to an excel file
        csv_df.to_excel(result_xlsx, index=False)
        # saving the excel file
        result_xlsx.save()

    @staticmethod
    def create_sub_folder(working_dir, folder_name):
        sub_working_dir = os.path.join(working_dir, folder_name)
        if not os.path.exists(sub_working_dir):
            os.makedirs(sub_working_dir)
        return sub_working_dir

    @staticmethod
    def delete_last_created_folder(path):
        os.chdir(path)
        l = []
        for dir in os.listdir(path):
            # get the name of the last created dir
            abs_path = os.path.abspath(dir)
            l.append(os.path.getctime(abs_path))
        dir_to_delete = max(l)
        for dir in os.listdir(path):
            abs_path = os.path.abspath(dir)
            if os.path.getctime(abs_path) == dir_to_delete:
                shutil.rmtree(abs_path)
                break

    @staticmethod
    def convert_txt_to_csv(txt_file_path):
        ext = '.txt'
        os.chdir(txt_file_path)
        for file in os.listdir(txt_file_path):
            if file.endswith(ext):
                try:
                    df = pd.read_csv(file, header=None, delim_whitespace=True, low_memory=False)
                    df.to_csv(file + '.csv', index=False, header=None)
                    print('file changed from .txt to .csv successfully')
                    e = 0
                except EmptyDataError:
                    e = 1
                    print(
                        'No columns to parse from file (.txt to .csv), file size is 0 kb or the downloaded file is bugged')
                if e == 1:
                    print(
                        "Downloaded file is corrupted because file size is 0 kb or the downloaded is bugged, need to redownload the same file")
                    time.sleep(1)
                    # move back one sub directory
                    os.chdir('../UNDP_Data')
                    shutil.rmtree(txt_file_path)
                    print('Sub folder deleted')
        return e

    @staticmethod
    def convert_txt_to_xlsx(txt_file_path):
        ext = '.txt'
        os.chdir(txt_file_path)
        for file in os.listdir(txt_file_path):
            if file.endswith(ext):
                try:
                    df = pd.read_csv(file, header=None, delim_whitespace=True, low_memory=False)
                    df.to_excel(file + '.xlsx', index=False, header=None)
                    print('file changed from .txt to .xlsx successfully')
                    e = 0
                except EmptyDataError:
                    e = 1
                    print(
                        'No columns to parse from file (.txt to .xlsx), file size is 0 kb or the downloaded file is bugged, need to redownload')
                if e == 1:
                    print(
                        "Downloaded file is corrupted because file size is 0 kb or the downloaded is bugged, need to redownload the same file")
                    time.sleep(1)
                    # move back one sub directory
                    os.chdir('../UNDP_Data')
                    shutil.rmtree(txt_file_path)
                    print('Sub folder deleted')

    @staticmethod
    def check_download_status(download_dir, downloaded_file_extension):
        recheck = True
        timer = 0
        while recheck:
            for file in os.listdir(download_dir):
                if not file.endswith(downloaded_file_extension):
                    print(f'Downloading..{timer}')
                    time.sleep(1)
                    timer += 1
                if timer == 3000:
                    print('Download failed, it never started, try to repress the download button after refreshing.')
                    recheck = False
                if file.endswith(downloaded_file_extension) and timer < 3000:
                    print('Download is done!')
                    recheck = False
        return timer

    @staticmethod
    def move_file_from_downloads(download_dir, target_dir, downloaded_file_name_change_to,
                                 downloaded_file_extention):
        os.chdir(download_dir)
        for file in os.listdir(download_dir):
            if file.endswith(downloaded_file_extention):
                shutil.move(file, os.path.join(target_dir, downloaded_file_name_change_to + downloaded_file_extention))
                print(f'{downloaded_file_extention} file renamed and moved to: ' + os.path.join(target_dir,
                                                                                                downloaded_file_name_change_to + downloaded_file_extention))
                logging.info(f'{downloaded_file_extention} file renamed and moved to: ' + os.path.join(target_dir,
                                                                                                       downloaded_file_name_change_to + downloaded_file_extention))
                time.sleep(3)

    @staticmethod
    def unzip_files(path, extension):
        # change path from working dir to dir with files
        os.chdir(path)
        all_subdirs = []
        # loop through items in dir
        for items in os.walk(path):
            # check for ".zip" extension
            all_subdirs.append(items[0])
        for subdir in all_subdirs:
            os.chdir(subdir)
            for item in os.listdir(subdir):
                try:
                    if item.endswith(extension) and extension == '.zip':
                        print('to unzip: ' + item)
                        # get full path of files
                        file_name = os.path.abspath(item)
                        # create zipfile object
                        zip_ref = zipfile.ZipFile(file_name)
                        # create folder with file_name
                        os.makedirs(item[:-4])
                        new_dir = os.path.join(subdir, item[:-4])
                        os.chdir(new_dir)
                        # extract file to dir
                        zip_ref.extractall(new_dir)
                        print('unzipped ' + item + extension + ' file')
                        # close file
                        zip_ref.close()
                        # delete zipped file
                        os.remove(file_name)
                        print('deleted ' + item + ' file')
                        # revert to master dir
                        os.chdir(path)
                    elif item.endswith(extension) and extension == '.gz':
                        print('to unzip: ' + item)
                        # get file name
                        file_name = item
                        # create folder with file_name
                        os.makedirs(item[:-3])
                        new_dir = os.path.join(subdir, item[:-3])
                        # extract file to dir
                        with gzip.open(file_name, 'r') as f_in:
                            with open(os.path.join(new_dir, file_name + '.txt'), 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        print('unzipped ' + item + ' file')
                        # delete zipped file
                        os.remove(file_name)
                        print('deleted ' + item + ' file')
                        # revert to master dir
                        os.chdir(path)
                except BadZipFile:
                    print(file_name + ' is corrupted u will have to unzip it manually.')
                    continue

    @staticmethod
    def convert_xls_to_xlsx(path):
        # converting .xls to .xlsx
        l = []
        for x in os.listdir(path):
            l.append(x)
        for i in range(len(l)):
            current_dir = os.path.join(path, l[i])
            if os.path.isdir(current_dir):
                for file in os.listdir(current_dir):
                    if file.endswith('.xls'):
                        fname = os.path.join(current_dir, file)
                        excel = win32.gencache.EnsureDispatch('Excel.Application')
                        wb = excel.Workbooks.Open(fname)

                        wb.SaveAs(fname + "x", FileFormat=51)  # FileFormat = 51 is for .xlsx extension
                        wb.Close()  # FileFormat = 56 is for .xls extension
                        excel.Application.Quit()

    @staticmethod
    def convert_dataset_to_json_dynamically(path, source, source_description, source_url, trigger_talend: bool):
        for file in os.listdir(path):
            # print(file)
            if 'Metadata' in file and file.endswith('.json'):
                print(file)
                logging.info(file)
                with open(os.path.join(path, file), 'r') as f:
                    file_metadata = json.load(f)
                    break
            else:
                # no metadata (empty dict)
                file_metadata = {}
        for file in os.listdir(path):
            if 'Metadata' not in file and (file.endswith('.csv') or file.endswith('.xlsx') or file.endswith('.xls')):
                raw_data = file
                break
            else:
                raw_data = None
        if raw_data is None:
            print('no .csv or .xlsx or .xlsx file found')
            logging.info('no .csv or .xlsx or .xlsx file found')
            return

        print(raw_data)
        logging.info(raw_data)

        new_path = path.replace('Z:', '//10.30.31.77/data_collection_dump')
        new_path2 = new_path.replace("\\", "/")

        BodyDict = {

            "JobPath": f"{new_path2}/{raw_data}",
            "JsonDetails": {
                ## Required
                "organisation": "un-agencies",
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
                # "SavePathForJsonOutput": ""
                # test
                "SavePathForJsonOutput": "//10.30.31.77/data_collection_dump/TestData/"
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
    def convert_scraped_data(path, source, source_description, source_url, trigger_talend: bool):
        l = []
        c = 0
        for x in os.listdir(path):
            l.append(x)
        for i in range(len(l)):
            # print(l[i])
            current_dir = os.path.join(path, l[i])
            if os.path.isdir(current_dir):
                # print(current_dir)
                for file in os.listdir(current_dir):
                    # print(file)
                    if 'Metadata' in file and file.endswith('.json'):
                        print(file)
                        logging.info(file)
                        with open(os.path.join(current_dir, file), 'r') as f:
                            file_metadata = json.load(f)
                            break
                    else:
                        # no metadata (empty dict)
                        file_metadata = {}
                for file in os.listdir(current_dir):
                    if 'Metadata' not in file and (
                            file.endswith('.csv') or file.endswith('.xlsx') or file.endswith('.xls')):
                        print(file)
                        logging.info(file)
                        raw_data = file
                        break
                    else:
                        raw_data = None
            if raw_data is None:
                continue

            new_path = current_dir.replace('Z:', '//10.30.31.77/data_collection_dump')
            new_path2 = new_path.replace("\\", "/")

            BodyDict = {

                "JobPath": f"{new_path2}/{raw_data}",
                "JsonDetails": {
                    ## Required
                    "organisation": "un-agencies",
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
                    # real
                    "SavePathForJsonOutput": ""
                    # test
                    # "SavePathForJsonOutput": "//10.30.31.77/data_collection_dump/TestData/"
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

        print('print triggered talend')
# if __name__ == "__main__":
#     RequestRunJobTalendClass = RequestRunJobTalend()
#     #RequestRunJobTalendClass.TriggerTalendckanJob()
#     RequestRunJobTalendClass.TriggerTalenddeltaJob()
