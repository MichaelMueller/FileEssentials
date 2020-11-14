import abc
from typing import List, Dict, Tuple, Union


# ABSTRACT DESIGN
class FilesSource:
    """
    retrieve a list of file_paths
    """

    @abc.abstractmethod
    def get(self) -> List[str]:
        return None


class Parameter:
    # integral types
    STRING = 0
    INT = 1
    FLOAT = 2
    BOOL = 3
    # semantic types
    REF = 4
    DIR = 5
    FILE = 6

    @abc.abstractmethod
    def name(self) -> str:
        return None

    @abc.abstractmethod
    def value(self) -> Union[str, int, float, bool]:
        return None

    @abc.abstractmethod
    def setValue(self, value):
        return None

    @abc.abstractmethod
    def type(self) -> int:
        return None

    @abc.abstractmethod
    def description(self) -> str:
        return None


class FilesFunction:
    """
    get a string representation of a FilesFunction (Filter or Processor)
    """

    @abc.abstractmethod
    def to_String(self) -> str:
        return self.__class__.__name__

    @abc.abstractmethod
    def parameters(self) -> List[Parameter]:
        return None


class FilesFilter(FilesFunction):
    """
    filter the list of file_paths
    :returns a list of filtered file paths
    """

    @abc.abstractmethod
    def filter(self, files: List[str]) -> List[str]:
        return None


class FilesProcessor(FilesFunction):
    """
    process the list of file_paths
    :returns a list of errors during processing (empty if no errors occured)
    """

    @abc.abstractmethod
    def process(self, files: List[str]) -> List[str]:
        return None


class Log:

    @abc.abstractmethod
    def info(self, message):
        pass

    @abc.abstractmethod
    def warn(self, message):
        pass

    @abc.abstractmethod
    def error(self, message):
        pass

    @abc.abstractmethod
    def debug(self, message):
        pass
