import json
import os
import sys
import tempfile

import interfaces
from typing import Dict, List
from datetime import datetime
from inspect import getframeinfo, stack, getmembers, isfunction


# Classes
class Property:
    def __init__(self, name, default=None):
        self.name = name
        self.value = None
        self.help = None


class Args(interfaces.Args):

    def __init__(self, args: Dict):
        self.args = args

    def get(self, key: str, default=None):
        return self.args[key] if key in self.args.keys() else default


class ArgvArgs(interfaces.Args):
    def __init__(self):
        self._args = None  # Initial value

    @property
    def args(self):
        if self._args is None:
            args = {}
            num_args = len(sys.argv)
            next_numeric_key = 0
            i = 1
            while i < num_args:
                arg = sys.argv[i]  # type: str
                curr_key = None
                if arg.startswith("--") and len(arg) > 2:
                    curr_key = arg[2:].lower()
                elif arg.startswith("-") and len(arg) > 1:
                    curr_key = arg[1:].lower()
                if curr_key:
                    i = i + 1
                    arg = sys.argv[i] if i < num_args else None
                    args[curr_key] = arg
                else:
                    args[next_numeric_key] = arg
                    next_numeric_key = next_numeric_key + 1
                i = i + 1
            self._args = args
        return self._args

    def get(self, key: str, default=None):
        return self.args[key] if key in self.args.keys() else default


# end of ArgvArgs

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
            complete_message = "[{}:{}]".format(os.path.basename(caller.filename), caller.lineno,
                                                message) + datetime.now().strftime(
                "[%Y/%m/%d %H:%M:%S]") + "[" + category.upper() + "]" + " " + message
            self.send_message(complete_message)

    def send_message(self, message, error=False):
        print(message, file=(sys.stderr if error else None))


class DirReader(interfaces.Source):
    def __init__(self, directory, recursive=True):
        self.directory = directory
        self.recursive = recursive

    def get(self, log: Log):
        log.info("reading from directory {}".format(self.directory))
        files = []
        for directory, sub_directories, file_names in os.walk(self.directory):
            for sub_directory in sub_directories:
                files.append(os.path.join(directory, sub_directory))
            for file_name in file_names:
                files.append(os.path.join(directory, file_name))

            if not self.recursive:
                break  # prevent descending into subfolders

        return sorted(files)


class FileFilter(interfaces.Filter):
    def filter(self, files: List[str], log: interfaces.Log) -> List[str]:
        log.info("filtering for files only")
        filtered_files = []
        for file in files:
            if os.path.isfile(file):
                filtered_files.append(file)
        return filtered_files


class FileSizeCalculator(interfaces.Processor):
    def process(self, files: List[str], log: interfaces.Log):
        log.info("collecting file size")
        file_size = 0
        for file in files:
            file_size = file_size + os.path.getsize(file)

        log.info("number of files: {}, size: {} MB".format(len(files), round(file_size / (1024 * 1024), 3)))
        return file_size


class Pipeline:
    def __init__(self, source: interfaces.Source):
        self.source = source  # type: interfaces.Source
        self.filters = []  # type: List[interfaces.Filter]
        self.processors = []  # type: List[interfaces.Processor]

    def exec(self, log: interfaces.Log):
        log.info("starting pipeline")
        results = []
        files = self.source.get(log)
        for files_filter in self.filters:
            files = files_filter.filter(files, log)
        for processor in self.processors:
            results.append(processor.process(files, log))
        return results


class PipelineSerializer:
    def __init__(self, log: interfaces.Log):
        self.log = log

    def to_dict(self, pipeline: Pipeline):
        dictionary = {}
        dictionary["source"] = self.instance_to_dict(pipeline.source)
        dictionary["filters"] = []
        for files_filter in pipeline.filters:
            dictionary["filters"].append(self.instance_to_dict(files_filter))
        dictionary["processors"] = []
        for processor in pipeline.processors:
            dictionary["processors"].append(self.instance_to_dict(processor))
        return dictionary

    def save_to_json_file(self, file_path: str, pipeline: Pipeline):
        # Serializing json
        json_object = json.dumps(self.to_dict(pipeline), indent=4)
        # Writing to sample.json
        with open(file_path, "w") as outfile:
            outfile.write(json_object)

    def get_class(self, obj):
        if obj.__class__.__module__ == self.__class__.__module__:
            return obj.__class__.__name__
        else:
            return "{0}.{1}".format(obj.__class__.__module__, obj.__class__.__name__)

    def instance_to_dict(self, obj) -> Dict:
        dic = {}
        dic["class"] = self.get_class(obj)
        dic["properties"] = obj.__dict__
        return dic


class PipelineUnserializer:
    def __init__(self, log: interfaces.Log):
        self.log = log

    def from_dict(self, dictionary: Dict):
        pipeline = Pipeline(self.dict_to_instance(dictionary["source"]))

        for files_filter in dictionary["filters"]:
            pipeline.filters.append(self.dict_to_instance(files_filter))
        for processor in dictionary["processors"]:
            pipeline.processors.append(self.dict_to_instance(processor))

        return pipeline

    def dict_to_instance(self, dictionary: Dict):
        klass = globals()[dictionary["class"]]
        instance = klass(**dictionary["properties"])
        return instance

    def load_from_json_file(self, file_path: str):
        with open(file_path, 'r') as openfile:
            # Reading from json file
            json_object = json.load(openfile)
            return self.from_dict(json_object)


class FileEssentials:

    def sandbox(self, args: interfaces.Args, log: interfaces.Log) -> int:
        # build pipeline
        pipeline = Pipeline(DirReader(os.getcwd()))
        pipeline.filters.append(FileFilter())
        pipeline.processors.append(FileSizeCalculator())
        pipeline.exec(log)

        # serialize
        temp_name = os.path.join(tempfile.gettempdir(), next(tempfile._get_candidate_names()))
        serializer = PipelineSerializer(log)
        serializer.save_to_json_file(temp_name, pipeline)
        json_file = open(temp_name, "r").read()
        log.info("contents: {}".format(json_file))

        # unserialize
        unserializer = PipelineUnserializer(log)
        pipeline_copy = unserializer.load_from_json_file(temp_name)
        pipeline_copy.exec(log)

        return 0

    def run(self, args: interfaces.Args, log: interfaces.Log) -> int:
        log.info("hello")
        return 0

    def boot(self, args: interfaces.Args, log: interfaces.Log) -> int:
        func_name = args.get("run", "run")
        method = getattr(self, func_name)
        if func_name is not "boot" and method is not None:
            return method(args, log)
        else:
            log.error("function '{}' unknown".format(func_name), "run")
            return -1
