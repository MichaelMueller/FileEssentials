import fe_interfaces
from typing import List


class NoneFilter(fe_interfaces.FilesFilter):

    def filter(self, files: List[str]) -> List[str]:
        return files


class NoneProcessor(fe_interfaces.FilesProcessor):

    def process(self, files: List[str]) -> List[str]:
        return []


class FileEssentials:

    def __init__(self):
        self.files = []  # type: List[str]
        self.filesFilters = []  # type: List[fe_interfaces.FilesFilter]
        self.filesProcessors = []  # type: List[fe_interfaces.FilesProcessor]
