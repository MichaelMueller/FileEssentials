import os, sys
import abc
from typing import List, Dict, Tuple, Union
from datetime import datetime
from inspect import getframeinfo, stack


class Log:

    def __init__(self, log_level="info"):
        self.log_level = log_level
        self.log_levels = {"debug": 10, "info": 20, "warn": 30, "error": 40}
        self.errors = {}
        self.warnings = {}

    def error(self, message, param_name=None):
        if param_name not in self.errors.keys():
            self.errors[param_name] = []
        self.errors[param_name].append(message)
        self.build_and_send_message("error", (param_name + ": " if param_name else "") + message, error=True)

    def info(self, message):
        self.build_and_send_message("info", message)

    def warn(self, message, param_name=None):
        if param_name not in self.warnings.keys():
            self.warnings[param_name] = []
        self.warnings[param_name].append(message)
        self.build_and_send_message("warn", (param_name + ": " if param_name else "") + message)

    def debug(self, message):
        self.build_and_send_message("debug", message)

    def build_and_send_message(self, category, message, error=False):
        if self.log_levels[category] >= self.log_levels[self.log_level]:
            caller = getframeinfo(stack()[2][0])
            complete_message = "[{}:{}]".format(os.path.basename(caller.filename), caller.lineno, message)
            now = datetime.now()
            complete_message = complete_message + now.strftime("[%Y/%m/%d %H:%M:%S]")
            complete_message = complete_message + "[" + category.upper() + "]"
            complete_message = complete_message + " " + message
            self.send_message(complete_message)

    def send_message(message, error=False):
        print(message, file=(sys.stderr if error else None))


class FilesFilter:

    def filter(self, log: Log, files: List[str]) -> List[str]:
        return files


class FilesProcessor:

    def process(self, log: Log, files: List[str]) -> List[str]:
        return []


class DirReader:

    def __init__(self, directory, recursive=False):
        self.directory = directory
        self.recursive = recursive

    def get(self):
        files = []
        for directory, sub_directories, file_names in os.walk(self.directory):
            for sub_directory in sub_directories:
                files.append(os.path.join(directory, sub_directory))
            for file_name in file_names:
                files.append(os.path.join(directory, file_name))

            if not self.recursive:
                break  # prevent descending into subfolders

        return files


class Pipeline:

    def __init__(self):
        self.files_source = None  # type: List[str]
        self.files_filters = []  # type: List[FilesFilter]
        self.files_processors = []  # type: List[FilesProcessor]
        self.log = None  # type: Log

    def filter(self, files: List[str]) -> List[str]:
        for files_filter in self.files_filters:
            files = files_filter.filter(files)
        return files

    def process(self, files: List[str]) -> List[str]:
        return []
