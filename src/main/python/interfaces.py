import abc
from typing import List, Dict, Tuple


# Interfaces
class Args:

    @abc.abstractmethod
    def get(self, key: str, default=None):
        return None


class Log:

    @abc.abstractmethod
    def error(self, error, param_name=None):
        pass

    @abc.abstractmethod
    def warn(self, warning, param_name=None):
        pass

    @abc.abstractmethod
    def info(self, message):
        pass

    @abc.abstractmethod
    def debug(self, message):
        pass


class Source:
    @abc.abstractmethod
    def get(self, log: Log) -> List[str]:
        return None


class Filter:
    @abc.abstractmethod
    def filter(self, files: List[str], log: Log) -> List[str]:
        return None


class Processor:
    @abc.abstractmethod
    def process(self, files: List[str], log: Log):
        return None
