from imf_datamanipulator import ImfpManipulator
import imfp

# https://github.com/chriscarrollsmith/imfp
imf = ImfpManipulator()

# imf.view_input_codes_and_description_of_database_valid_parameters(database_id='IFS_2019M01')
imf.sort_databases_by_indicator_or_commodity()
