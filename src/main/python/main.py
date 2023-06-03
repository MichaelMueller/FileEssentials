# sys imports
import sys, os, datetime, abc
from typing import Union

# pip imports
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QListWidget, QFileDialog, QAbstractItemView, QMessageBox, QProgressDialog, QApplication, QLabel, QTextEdit, \
    QSplitter, QGroupBox, QMainWindow, QComboBox, QMdiArea, QMenu, QAction

# interfaces and abstract classes    
class FileEssentialsObject:  
    @abc.abstractclassmethod
    def name( self ) -> str:
        raise NotImplementedError()

    @abc.abstractclassmethod
    def description( self ) -> str:
        raise NotImplementedError
        
    def set_process_directory( self, process_directory:str ) -> None:
        pass
    
class FileFilter(FileEssentialsObject):    
    @abc.abstractclassmethod
    def use_file( self, file_path:str ) -> bool:
        raise NotImplementedError()
    
class FileProcessor(FileEssentialsObject):    
    @abc.abstractclassmethod
    def process( self, file_path:str ) -> None:
        raise NotImplementedError()    
        
class FileFilterWidget(QWidget, FileFilter):   
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
    
class FileProcessorWidget(QWidget, FileProcessor):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

class FileEssentialsRegistry:

    @abc.abstractclassmethod    
    def add_file_filter( self, file_filter:FileFilter ) -> None:
        raise NotImplementedError()
    
    @abc.abstractclassmethod    
    def add_file_processor( self, file_processor_widget:FileProcessor ) -> None:
        raise NotImplementedError()

    @abc.abstractclassmethod    
    def active_processor( self ) -> FileProcessor:
        raise NotImplementedError()
    
    @abc.abstractclassmethod        
    def use_file( self, file_path:str ) -> bool:
        raise NotImplementedError()       
        
    @abc.abstractclassmethod        
    def set_process_directory( self, process_directory:str ) -> None:
        raise NotImplementedError()       

class FilePrinter(FileProcessorWidget):
    def __init__(self, parent=None):
        FileProcessorWidget.__init__(self, parent)

        self._text_widget = QTextEdit()
        self._text_widget.setDisabled(True)

        layout = QVBoxLayout()
        layout.addWidget( self._text_widget )

        self.setLayout(layout)
        
    def name( self ) -> str:
        return "File Printer"

    def description( self ) -> str:
        return "Prints the path for each file"
    
    def process( self, file_path:str ) -> bool:
        html = f"<b>{file_path}</b><br>"
        self._text_widget.insertHtml( html )

    def set_process_directory( self, process_directory:str ) -> None:
        self._text_widget.setHtml("Processing directory "+process_directory)

class FileStatisticsPrinter(FileProcessorWidget):
    def __init__(self, parent=None):
        FileProcessorWidget.__init__(self, parent)

        self._text_widget = QTextEdit()
        self._text_widget.setDisabled(True)

        layout = QVBoxLayout()
        layout.addWidget( self._text_widget )

        self.setLayout(layout)
        
    def name( self ) -> str:
        return "File Statistics Printer"

    def description( self ) -> str:
        return "Prints statistics for each file"
    
    def process( self, file_path:str ) -> bool:
        statistics = { "size": os.stat(file_path).st_size, "last_modified": os.stat(file_path).st_mtime }
        html = f"<b>{file_path}</b>: {statistics}<br>"
        self._text_widget.insertHtml( html )

    def set_process_directory( self, process_directory:str ) -> None:
        self._text_widget.setHtml("Processing directory "+process_directory)
    
class FileOrFolderFilter(FileProcessorWidget):
    def __init__(self, parent=None):
        FileProcessorWidget.__init__(self, parent)

        self._process_directory = None

        self._choice = QComboBox()
        self._choice.addItem("Files and Folders")
        self._choice.addItem("Only Files")
        self._choice.addItem("Only Folders")

        layout = QVBoxLayout()
        layout.addWidget( QLabel("Enter allowed file items") )
        layout.addWidget( self._choice )
        layout.addStretch()

        self.setLayout(layout)
        
    def set_process_directory( self, process_directory:str ) -> None:
        self._process_directory = process_directory

    def name( self ) -> str:
        return "File or Folder Filter"

    def description( self ) -> str:
        return "Filters files, folders or both"
    
    def use_file( self, file_path:str ) -> bool:
        
        if self._choice.currentText() == "Files and Folders":
            return True
        elif self._choice.currentText() == "Only Folders":
            return os.path.isdir( os.path.join( self._process_directory, file_path ) )
        elif self._choice.currentText() == "Only Files":
            return os.path.isfile( os.path.join( self._process_directory, file_path ) )
    
class FileExtensionFilter(FileProcessorWidget):
    def __init__(self, parent=None):
        FileProcessorWidget.__init__(self, parent)

        self._extensions_input = QLineEdit()

        layout = QVBoxLayout()
        layout.addWidget( QLabel("Enter allowed extensions (e.g. \"*.jpg; *.txt\")") )
        layout.addWidget( self._extensions_input )
        layout.addStretch()

        self.setLayout(layout)
        
    def name( self ) -> str:
        return "File Extension Filter"

    def description( self ) -> str:
        return "Filters files by their extension"
    
    def use_file( self, file_path:str ) -> bool:
        use_file = False
        allowed_file_extensions:list[str] = self._extensions_input.text().split(";")
        if self._extensions_input.text() == "" or len( allowed_file_extensions ) == 0:
            use_file = True
        else:
            allowed_file_extensions = [ allowed_file_extension.strip().replace("*.", ".").lower() for allowed_file_extension in allowed_file_extensions ]        
            _, file_ext = os.path.splitext(file_path)
            use_file = file_ext.lower() in allowed_file_extensions or ".*" in allowed_file_extensions       
        print(f'use_file: {use_file}')
        return use_file

class FesDirChooser(QWidget):
    def __init__(self, fes_registry:FileEssentialsRegistry, parent=None):
        QWidget.__init__(self, parent)
        self._fes_registry = fes_registry
        # build gui

        # left pane: 
        # Directory->Filter->File List
        self._dir_input = QLineEdit()
        self._dir_input.setDisabled(True)
        self._dir_input.setStyleSheet("min-width: 240px;")

        dir_button = QPushButton("Select Directory")
        dir_button.clicked.connect(self.dir_button_clicked)

        self._reprocess_button = QPushButton("Reprocess")
        self._reprocess_button.clicked.connect(self.reprocess_button_clicked)
        self._reprocess_button.setDisabled(True)

        # self layout
        layout = QVBoxLayout()
        layout.addWidget(self._dir_input)
        layout.addWidget(dir_button)
        layout.addWidget(self._reprocess_button)
        layout.addStretch()
        self.setLayout(layout)
   
    def set_process_directory( self, process_directory:Union[str,None], user:bool=None ) -> None:        
        if process_directory:
            self._fes_registry.set_process_directory( process_directory )
            self._reprocess_button.setDisabled(False)
            self._dir_input.setText(process_directory)
            self.process_directory(process_directory)
        else:            
            self._reprocess_button.setDisabled(True)
            self._dir_input.setText("")

    def reprocess_button_clicked(self):
        self.set_process_directory( self._dir_input.text(), True )

    def dir_button_clicked(self):
        # self.file_list.clear()
        # self.file_list.setEnabled(False)
        #self.output_file_widget.setEnabled(False)
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory") )
        self.set_process_directory(dir, True)

    def process_directory(self, process_directory):
        self.progress_dialog = QProgressDialog("Processing ...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.show()
        # pdf file search
        files = []
        i = 1
        file_processor = self._fes_registry.active_processor()

        for root, dirnames, filenames in os.walk(process_directory):                          
            if self.progress_dialog.wasCanceled():
                return []
            self.progress_dialog.setValue(i)
            QApplication.processEvents()

            i = i + 1 if i < 100 else 0

            for file_item in dirnames + filenames:                
                #print(f'{file_path}')
                if self._fes_registry.use_file( file_item ):
                    if file_processor:
                        file_processor.process( file_item )

        self.progress_dialog.close()
        self.progress_dialog = None
        return files
    

class FesMainWindow(QMainWindow, FileEssentialsRegistry):
    def __init__(self):
        super().__init__()

        # state vars
        self._filters:list[FileFilter] = []
        self._processors:list[FileProcessor] = []

        # widgets
        self.mdi:QMdiArea = None
        self._filters_menu:QMenu = None
        self._processors_menu:QMenu = None

        # build ui
        self._build_ui()

        # add default filters and processors
        self.add_file_filter( FileExtensionFilter() )
        self.add_file_filter( FileOrFolderFilter() )
        self.add_file_processor( FilePrinter() )
        self.add_file_processor( FileStatisticsPrinter() )

    def _build_ui(self) -> None:
        self._mdi = QMdiArea()
        self._mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # add subwindow
        subwindow = self._mdi.addSubWindow(FesDirChooser( self ), QtCore.Qt.WindowMinMaxButtonsHint )
        subwindow.setWindowTitle("Choose Directory")
        subwindow.show()

        # other menus
        self._filters_menu = self.menuBar().addMenu('Filters')
        self._processors_menu = self.menuBar().addMenu('Processors')

        # window menu
        windows_menu = self.menuBar().addMenu('Windows')
        cascade_action = windows_menu.addAction("Cascade")
        cascade_action.triggered.connect( lambda checked: self._mdi.cascadeSubWindows() )
        tile_action = windows_menu.addAction("Tile")
        tile_action.triggered.connect( lambda checked: self._mdi.tileSubWindows() )
        
        self.setCentralWidget(self._mdi)    
        self.setWindowTitle("File Essentials")
        self.show()

    def file_filter(self, name:str) -> Union[FileFilter, None]:        
        for file_filter in self._filters:
            if file_filter.name() == name:
                return file_filter            
        return None

    def file_processor(self, name:str) -> Union[FileProcessor, None]:
        for file_processor in self._processors:
            if file_processor.name() == name:
                return file_processor            
        return None

    def add_file_filter( self, file_filter:FileFilter ) -> None:
        if self.file_filter(file_filter.name() ) != None:
            sys.stderr.write(f"FileFilter \"{file_filter.name()}\" already added!\n")
            return

        # set as parent
        if isinstance(file_filter, QWidget):
            file_filter.setParent(self)
        self._filters.append( file_filter )

        # rebuild menu
        self._filters_menu.clear()
        for filter in self._filters:
            action = self._filters_menu.addAction( filter.name() )
            action.setObjectName( filter.name() )
            action.triggered.connect( self._filter_action_clicked )
            action.setCheckable(True)
         
    def set_process_directory( self, process_directory:str ) -> None:
        for file_essentials_object in self._filters + self._processors:
            file_essentials_object.set_process_directory(process_directory)

    def add_file_processor( self, file_processor:FileProcessor ) -> None:
        if self.file_processor(file_processor.name() ) != None:
            sys.stderr.write(f"FileProcessor \"{file_processor.name()}\" already added!\n")
            return
        
        # set as parent
        if isinstance(file_processor, QWidget):
            file_processor.setParent(self)
        self._processors.append( file_processor )

        # rebuild menu
        self._processors_menu.clear()
        for processor in self._processors:

            action = self._processors_menu.addAction( processor.name() )
            action.setObjectName( processor.name() )
            action.triggered.connect( self._processor_action_clicked )
            action.setCheckable(True)

    def active_processor( self ) -> Union[None, FileProcessor]:        
        for curr_action in self._processors_menu.actions():
            if curr_action.isChecked():
                return self.file_processor( curr_action.objectName() )
        return None

    def _filter_action_clicked( self, checked:bool ):
        # get sender and filter
        # get sender and processor
        action = self.sender()
        filter_name = action.objectName()
        #print(f"Found action for processor {processor_name}")     
        filter = self.file_filter(filter_name)
                
        if isinstance(filter, QWidget):
            subwindow = None                    
            for curr_subwindow in self._mdi.subWindowList():
                if curr_subwindow.windowTitle() == filter.name():
                    subwindow = curr_subwindow
                    break
            
            if not subwindow:
                subwindow = self._mdi.addSubWindow(filter, QtCore.Qt.WindowMinMaxButtonsHint)
                subwindow.setWindowTitle(filter.name())
                                
            subwindow.show() if checked else subwindow.hide()

    def _processor_action_clicked( self, checked:bool ):   
        # get sender and processor
        action = self.sender()
        processor_name = action.objectName()
        #print(f"Found action for processor {processor_name}")     
        processor = self.file_processor(processor_name)

        # Hide all processor windows and show the one that is used
        subwindow = None                   
        if isinstance(processor, QWidget): 
            for curr_subwindow in self._mdi.subWindowList():
                if isinstance( curr_subwindow.widget(), FileProcessor ):
                    if curr_subwindow.windowTitle() == processor_name:
                        subwindow = curr_subwindow
                    curr_subwindow.hide()
            
            if not subwindow:
                subwindow = self._mdi.addSubWindow(processor, QtCore.Qt.WindowMinMaxButtonsHint)
                subwindow.setWindowTitle(processor_name)

        # uncheck all actions
        for curr_action in self._processors_menu.actions():
            curr_action.setChecked(False)
        
        action.setChecked( checked )
        if subwindow:
            subwindow.show() if checked else subwindow.hide()

    def use_file( self, file_path:str ) -> bool:
        active_filters:list[FileFilter] = []
        for curr_action in self._filters_menu.actions():
            if curr_action.isChecked():
                active_filters.append( self.file_filter( curr_action.objectName() ) )
        
        # check
        for filter in active_filters:
            if filter.use_file( file_path ) == False:
                return False
        return True
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    fes_main_window = FesMainWindow()
    app.exec_()
