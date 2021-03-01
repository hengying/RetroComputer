import time
import threading
import configparser
from themes import *

class SingletonType(type):
    _instance_lock = threading.Lock()
    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            with SingletonType._instance_lock:
                if not hasattr(cls, "_instance"):
                    cls._instance = super(SingletonType,cls).__call__(*args, **kwargs)
        return cls._instance

class Config(metaclass=SingletonType):
    def __init__(self):
        self.__config = configparser.ConfigParser()
        self.__config_file = "config.ini"
        self.__config.read(self.__config_file)

        if self.__config.has_option('win', 'win_pos_x'):
            self._win_pos_x = int(self.__config.get('win', 'win_pos_x'))
        else:
            self._win_pos_x = None

        if self.__config.has_option('win', 'win_pos_y'):
            self._win_pos_y = int(self.__config.get('win', 'win_pos_y'))
        else:
            self._win_pos_y = None

        self._win_width = 1280
        self._win_height = 400

        self._show_cursor = int(self.__config.get('win', 'show_cursor')) == 1

        self._theme_name = self.__config.get('win', 'theme_name')

        #self._fps = 60
        self._fps = 30

    @property
    def win_pos_x(self):
        return self._win_pos_x

    @property
    def win_pos_y(self):
        return self._win_pos_y

    @property
    def win_width(self):
        return self._win_width

    @property
    def win_height(self):
        return self._win_height

    @property
    def fps(self):
        return self._fps

    @property
    def show_cursor(self):
        return self._show_cursor

    def save_config_file(self):
        self.__config.write(open(self.__config_file, "w"))

    @property
    def background_color(self):
        return themes[self._theme_name]['background_color']

    @property
    def active_background_color(self):
        return themes[self._theme_name]['active_background_color']

    @property
    def text_color(self):
        return themes[self._theme_name]['text_color']

    @property
    def highlight_text_color(self):
        return themes[self._theme_name]['highlight_text_color']


