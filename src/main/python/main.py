# sys imports
import sys, os, datetime, abc
from typing import Union

# pip imports
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QListWidget, QFileDialog, QAbstractItemView, QMessageBox, QProgressDialog, QApplication, QLabel, QTextEdit, \
    QSplitter, QGroupBox, QMainWindow, QComboBox, QMdiArea

# interfaces and abstract classes    
class FileEssentialsObject:  
    @abc.abstractclassmethod
    def name( self ) -> str:
        raise NotImplementedError()

    @abc.abstractclassmethod
    def description( self ) -> str:
        raise NotImplementedError()
    
class FileFilter(FileEssentialsObject):    
    @abc.abstractclassmethod
    def use_file( self, file_path:str ) -> bool:
        raise NotImplementedError()
    
class FileProcessor(FileEssentialsObject):    
    @abc.abstractclassmethod
    def process( self, file_path:str ) -> bool:
        raise NotImplementedError()
        
class FileFilterWidget(QWidget, FileFilter):   
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
    
class FileProcessorWidget(QWidget, FileProcessor):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

class FileEssentialsRegistry(FileFilter):

    @abc.abstractclassmethod    
    def add_file_filter( self, file_filter:FileFilter ) -> None:
        raise NotImplementedError()
    
    @abc.abstractclassmethod    
    def add_file_processor( self, file_processor_widget:FileProcessor ) -> None:
        raise NotImplementedError()

    @abc.abstractclassmethod    
    def selected_processor( self ) -> FileProcessor:
        raise NotImplementedError()


# class Fes(QWidget):
#     def __init__(self, parent=None):
#         QWidget.__init__(self, parent)
#         # build gui

#         # left pane: 
#         # Directory->Filter->File List
#         dir_input = QLineEdit()
#         dir_input.setDisabled(True)
#         dir_button = QPushButton("Select Directory")
#         dir_button.clicked.connect(self.dir_button_clicked)
#         dir_layout = QVBoxLayout()
#         dir_layout.addWidget(dir_input)
#         dir_layout.addWidget(dir_button)
#         dir_box = QGroupBox("Directory")
#         dir_box.setLayout( dir_layout )

#         filters_layout = QVBoxLayout()
#         filters_box = QGroupBox("Filters")

#         files_layout = QVBoxLayout()
#         self._files_box = QGroupBox("Files")
#         self._files_box.setLayout( files_layout )
#         self._files_box.setDisabled(True)
        
#         self._console_widget = QTextEdit("")
#         self._console_widget.setReadOnly(True)
#         console_layout = QVBoxLayout()
#         console_layout.addWidget(self._console_widget)
#         self._console_box = QGroupBox("Console")
#         self._console_box.setLayout( console_layout )
#         self._console_box.setDisabled(True)

#         left_pane_layout = QVBoxLayout()
#         layout.addWidget(splitter)
#         layout.addWidget(self._files_box)
#         layout.addWidget(self._console_box)
#         left_pane = QWidget()
#         left_pane.setLayout(layout)

#         # RIGHT PANE
#         processor_chooser = QComboBox()
#         processor_chooser.addItem("Determine size")
#         processor_chooser_layout = QVBoxLayout()
#         processor_chooser_box = QGroupBox("Choose Processor:")

#         right_pane_layout = QVBoxLayout()
#         right_pane_layout.addWidget(splitter)
#         right_pane_layout.addWidget(self._files_box)
#         right_pane_layout.addWidget(self._console_box)
#         left_pane = QWidget()
#         left_pane.setLayout(layout)

#         # left/right pane splitter
#         splitter = QSplitter(Qt.Horizontal)
#         splitter.addWidget(left_widget)
#         splitter.addWidget(right_widget)

#         # self layout
#         layout = QVBoxLayout()
#         layout.addWidget(splitter)
#         layout.addWidget(self._files_box)
#         layout.addWidget(self._console_box)
#         self.setLayout(layout)


#     def dir_button_clicked(self):
#         # self.file_list.clear()
#         # self.file_list.setEnabled(False)
#         #self.output_file_widget.setEnabled(False)
#         dir = str (QFileDialog.getExistingDirectory(self, "Select Directory") )
#         if dir:
#             files = self.scan_files(dir)
#             # for file in files:
#             #     self.file_list.addItem(file)
#             # if len(files) > 0:
#             #     # self.file_list.setEnabled(True)
#             #     self.output_file_widget.setEnabled(True)

#     def scan_files(self, dir_path):
#         self.progress_dialog = QProgressDialog("Processing ...", "Cancel", 0, 0, self)
#         self.progress_dialog.setWindowModality(Qt.WindowModal)
#         self.progress_dialog.setAutoReset(True)
#         self.progress_dialog.setAutoClose(False)
#         self.progress_dialog.show()
#         # pdf file search
#         files = []
#         i = 1
#         self.info(f'Scanning {dir_path}')
#         for root, dirnames, filenames in os.walk(dir_path):
#             for file in filenames:
#                 file_path = os.path.join(root, file)
#                 self.info(f'Processing {file_path}')
#                 if self.progress_dialog.wasCanceled():
#                     return []
#                 self.progress_dialog.setValue(i)
#                 QApplication.processEvents()

#                 i = i + 1 if i < 100 else 0
#                 # fname, fext = os.path.splitext(file)
#                 # if fext.lower() in self.get_supported_files():

#                 files.append(file_path)

#         self.progress_dialog.close()
#         self.progress_dialog = None
#         return files
    
#     def info(self, message):
#         self.log( message, "[INFO]")
    
#     def log(self, message, prefix:str=None):
#             complete_message = datetime.datetime.now().strftime("<b>[%Y/%m/%d %H:%M:%S]")
#             if prefix:
#                 complete_message += prefix
#             complete_message += ":</b>&nbsp;" + message
#             self._console_widget.setHtml( self._console_widget.toHtml() + "<br />" + complete_message )



class FesDirChooser(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        # build gui

        # left pane: 
        # Directory->Filter->File List
        dir_input = QLineEdit()
        dir_input.setDisabled(True)
        dir_button = QPushButton("Select Directory")
        dir_button.clicked.connect(self.dir_button_clicked)

        # self layout
        layout = QVBoxLayout()
        layout.addWidget(dir_input)
        layout.addWidget(dir_button)
        self.setLayout(layout)


    def dir_button_clicked(self):
        # self.file_list.clear()
        # self.file_list.setEnabled(False)
        #self.output_file_widget.setEnabled(False)
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory") )
        if dir:
            files = self.scan_files(dir)
            # for file in files:
            #     self.file_list.addItem(file)
            # if len(files) > 0:
            #     # self.file_list.setEnabled(True)
            #     self.output_file_widget.setEnabled(True)

    def scan_files(self, dir_path):
        self.progress_dialog = QProgressDialog("Processing ...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.show()
        # pdf file search
        files = []
        i = 1
        for root, dirnames, filenames in os.walk(dir_path):
            for file in filenames:
                file_path = os.path.join(root, file)
                
                if self.progress_dialog.wasCanceled():
                    return []
                self.progress_dialog.setValue(i)
                QApplication.processEvents()

                i = i + 1 if i < 100 else 0
                # fname, fext = os.path.splitext(file)
                # if fext.lower() in self.get_supported_files():

                files.append(file_path)

        self.progress_dialog.close()
        self.progress_dialog = None
        return files
    

class FesMainWindow(QMainWindow, FileEssentialsRegistry):
    def __init__(self):
        super().__init__()

        # state vars
        self._filters:list[FileFilter] = []
        self._active_filters:list[FileFilter] = []
        self._processors:list[FileProcessor] = []
        self._active_processor:Union[None, FileProcessor] = None

        # build ui
        self._build_ui()

    def _build_ui(self) -> None:
        mdi = QMdiArea()
        mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # add subwindow
        subwindow = mdi.addSubWindow(FesDirChooser())
        subwindow.setWindowTitle("Choose Directory")
        subwindow.show()

        # window menu
        windows_menu = self.menuBar().addMenu('Windows')
        cascade_action = windows_menu.addAction("Cascade")
        cascade_action.triggered.connect( lambda checked: mdi.cascadeSubWindows() )
        tile_action = windows_menu.addAction("Tile")
        tile_action.triggered.connect( lambda checked: mdi.tileSubWindows() )
        
        self.setCentralWidget(mdi)    
        self.setWindowTitle("File Essentials")
        self.show()


    @abc.abstractclassmethod    
    def add_file_filter( self, file_filter:FileFilter ) -> None:
        raise NotImplementedError()
    
    @abc.abstractclassmethod    
    def add_file_processor( self, file_processor_widget:FileProcessor ) -> None:
        raise NotImplementedError()

    @abc.abstractclassmethod    
    def selected_processor( self ) -> FileProcessor:
        raise NotImplementedError()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    fes_main_window = FesMainWindow()
    app.exec_()
