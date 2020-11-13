import abc
from typing import List, Dict, Tuple


# ABSTRACT DESIGN
class FilesSource:
    """
    retrieve a list of file_paths
    """

    @abc.abstractmethod
    def get(self) -> List[str]:
        return None


class FilesFunction:
    """
    get a string representation of a FilesFunction (Filter or Processor)
    """

    @abc.abstractmethod
    def to_String(self) -> str:
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
