
import os

BASIC_PROGRAM_FOLDER_NAME = 'BASIC'

def make_sure_basic_folder_exist():
    if not os.path.exists(BASIC_PROGRAM_FOLDER_NAME):
        os.mkdir(BASIC_PROGRAM_FOLDER_NAME)

def file_name_is_valid(filename):
    if filename.find('\\') != -1 or filename.find('/') != -1 or filename.find('..') != -1:
        return False
    else:
        return True
