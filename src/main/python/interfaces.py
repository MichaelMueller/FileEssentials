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


class SelfDescribingObject:

    @abc.abstractmethod
    def property_names(self):
        return None

    @abc.abstractmethod
    def property_(self):
        return None


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


class Property:
    pass


class Functor:

    @abc.abstractmethod
    def inputs(self) -> List[Property]:
        return None

    @abc.abstractmethod
    def outputs(self) -> List[Property]:
        return None

    @abc.abstractmethod
    def run(self, log: Log):
        pass
