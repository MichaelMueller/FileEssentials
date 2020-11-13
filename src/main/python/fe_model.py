import fe_interfaces
from typing import List


class NoneFilter(fe_interfaces.FilesFilter):

    def to_String(self) -> str:
        return "NoneFilter"

    def filter(self, files: List[str]) -> List[str]:
        return files


class NoneProcessor(fe_interfaces.FilesProcessor):

    def to_String(self) -> str:
        return "NoneProcessor"

    def process(self, files: List[str]) -> List[str]:
        return []
