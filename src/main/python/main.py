# sys imports
import sys, os, datetime, abc
from typing import Union

# pip imports
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QListWidget, QFileDialog, QAbstractItemView, QMessageBox, QProgressDialog, QApplication, QLabel, QTextEdit, \
    QSplitter, QGroupBox, QMainWindow, QComboBox, QMdiArea, QMenu, QAction, QErrorMessage

# base classes
class FesWidget(QWidget):  
    def global_settings() -> QSettings:
        settings = QSettings(QSettings.UserScope, "https://github.com/MichaelMueller", "File Essentials")
        return settings

    """ Base class for widget inside Fes (FileEssentials) """
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        
    def main_window( self ) -> Union[None, "FesMainWindow"]:
        curr_object = self
        while curr_object is not None and not isinstance( curr_object, FesMainWindow ):
            curr_object = curr_object.parent()
        return curr_object
    
class FilterOrProcessorWidget(FesWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._base_directory:str = None

    def before_processing( self, base_directory:str ) -> None:
        """ Called each time BEFORE the processing of the directory starts """
        self._base_directory = base_directory

    def settings( self ) -> QSettings:
        settings = FesWidget.global_settings()
        settings.beginGroup(self.name())
        return settings
    
    @abc.abstractclassmethod
    def name( self ) -> str:
        raise NotImplementedError()

    @abc.abstractclassmethod
    def description( self ) -> str:
        raise NotImplementedError

class FilterWidget(FilterOrProcessorWidget):    
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

    @abc.abstractclassmethod
    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        raise NotImplementedError()
    
class ProcessorWidget(FilterOrProcessorWidget):    
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

    @abc.abstractclassmethod
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> None:
        raise NotImplementedError()    

class FesDirChooser(FesWidget):
    """ The fundamental widget for choosing a directory """
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        # build UI
        self._base_directory = QLineEdit()
        self._base_directory.setDisabled(True)
        self._base_directory.setStyleSheet("min-width: 240px;")

        select_directory_button = QPushButton("Select Directory")
        select_directory_button.clicked.connect(self.select_directory_button_clicked)

        self._reprocess_button = QPushButton("Reprocess")
        self._reprocess_button.clicked.connect(self.reprocess_button_clicked)
        self._reprocess_button.setDisabled(True)

        layout = QVBoxLayout()
        layout.addWidget(self._base_directory)
        layout.addWidget(select_directory_button)
        layout.addWidget(self._reprocess_button)
        layout.addStretch()
        self.setLayout(layout)

        # restore values
        self.set_base_directory( FesWidget.global_settings().value("base_directory"), start_processing=False )
   
    def set_base_directory( self, base_directory:Union[str,None], start_processing:bool=True ) -> None:        
        if base_directory:
            if not os.path.isdir( base_directory ):
                error_dialog = QErrorMessage()
                error_dialog.showMessage(f'Not a directory: "{base_directory}"')
                return
            base_directory = os.path.abspath( base_directory )
            self._reprocess_button.setDisabled(False)
            self._base_directory.setText(base_directory)
            if start_processing:
                self._start_processing()
        else:            
            self._reprocess_button.setDisabled(True)
            self._base_directory.setText("")

        FesWidget.global_settings().setValue( "base_directory", base_directory )

    def reprocess_button_clicked(self):
        self._start_processing()

    def select_directory_button_clicked(self):
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory") )
        self.set_base_directory(dir, True)

    def _start_processing(self):
        # setup progress dialog
        progress_dialog = QProgressDialog("Processing ...", "Cancel", 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setAutoReset(True)
        progress_dialog.setAutoClose(False)
        progress_dialog.show()

        # collect files
        i = 0
        file_infos:list[tuple[str, str, int]] = []
        base_directory_abs_path = os.path.abspath( self._base_directory.text() )
        progress_dialog.setLabelText("Scanning files")
        for root, dirnames, filenames in os.walk(base_directory_abs_path):     
            if progress_dialog.wasCanceled():
                return
            QApplication.processEvents()

            level = root[len(base_directory_abs_path):].count(os.sep)
            for basename in dirnames + filenames:
                abs_path = os.path.join(root, basename)
                rel_path = abs_path.replace( base_directory_abs_path, "" )
                rel_path.replace( os.sep, "/" )
                file_infos.append( (abs_path, rel_path, level) )
                     
            i = i + 1 if i < 100 else 0
            progress_dialog.setValue(i)
        print(f'file_infos: {file_infos}')  

        # process files
        progress_dialog.setLabelText("Processing files")
        progress_dialog.setValue(0)
        main_window = self.main_window()
        main_window.before_processing( base_directory_abs_path )
        processor_widget = main_window.active_processor()
        one_percent = float( len(file_infos) ) / 100.0

        for i, file_info in enumerate(file_infos):            
            if progress_dialog.wasCanceled():
                return
            QApplication.processEvents()

            if main_window.use_file( file_info[0], file_info[1], file_info[2] ):
                if processor_widget:
                    processor_widget.process( file_info[0], file_info[1], file_info[2] )

            percent = round( one_percent / float(i+1) )
            progress_dialog.setValue( percent )

        progress_dialog.close()
        progress_dialog = None

class FilePrinter(ProcessorWidget):
    def __init__(self, parent=None):
        ProcessorWidget.__init__(self, parent)

        self._text_widget = QTextEdit()
        self._text_widget.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget( self._text_widget )

        self.setLayout(layout)
        
    def name( self ) -> str:
        return "File Printer"

    def description( self ) -> str:
        return "Prints the path for each file"
    
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        html = f"{rel_file_path}"
        self._text_widget.append( html )

    def before_processing( self, base_directory:str ) -> None:
        self._text_widget.setHtml("Processing directory <b>"+base_directory+"</b>")
        super().before_processing( base_directory )

class FileStatisticsPrinter(ProcessorWidget):
    def __init__(self, parent=None):
        ProcessorWidget.__init__(self, parent)


        self._text_widget = QTextEdit()
        self._text_widget.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget( self._text_widget )

        self.setLayout(layout)

    def name( self ) -> str:
        return "File Statistics Printer"

    def description( self ) -> str:
        return "Prints statistics for each file"
    
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        if os.path.isfile( abs_file_path ):
            stat = os.stat(abs_file_path)
            statistics = { "size": stat.st_size, "last_modified": stat.st_mtime }
            html = f"{rel_file_path}: {statistics}"
            self._text_widget.append( html )

    def before_processing( self, base_directory:str ) -> None:
        self._text_widget.setHtml("Processing directory <b>"+base_directory+"</b>")
        super().before_processing( base_directory )
    
class FileOrFolderFilter(FilterWidget):
    def __init__(self, parent=None):
        FilterWidget.__init__(self, parent)

        self._base_directory = None

        self._choice = QComboBox()
        self._choice.addItem("Files and Folders")
        self._choice.addItem("Only Files")
        self._choice.addItem("Only Folders")

        layout = QVBoxLayout()
        layout.addWidget( QLabel("Enter allowed file items") )
        layout.addWidget( self._choice )
        layout.addStretch()

        self.setLayout(layout)

    def name( self ) -> str:
        return "File or Folder Filter"

    def description( self ) -> str:
        return "Filters files, folders or both"
    
    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:        
        if self._choice.currentText() == "Files and Folders":
            return True
        elif self._choice.currentText() == "Only Folders":
            return os.path.isdir( abs_file_path )
        elif self._choice.currentText() == "Only Files":
            return os.path.isfile( abs_file_path )
    
class FileExtensionFilter(FilterWidget):
    def __init__(self, parent=None):
        FilterWidget.__init__(self, parent)

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
    
    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        use_file = False
        allowed_file_extensions:list[str] = self._extensions_input.text().split(";")
        if self._extensions_input.text() == "" or len( allowed_file_extensions ) == 0:
            use_file = True
        else:
            allowed_file_extensions = [ allowed_file_extension.strip().replace("*.", ".").lower() for allowed_file_extension in allowed_file_extensions ]        
            _, file_ext = os.path.splitext(abs_file_path)
            use_file = file_ext.lower() in allowed_file_extensions or ".*" in allowed_file_extensions       
        #print(f'use_file: {use_file}')
        return use_file

class FesMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # build widgets
        self._mdi = QMdiArea()
        self._mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # add subwindow
        subwindow = self._mdi.addSubWindow(FesDirChooser( self ), QtCore.Qt.WindowMinMaxButtonsHint )
        subwindow.setWindowTitle("Choose Directory")
        subwindow.show()

        # filter and processor menus
        self._filters_menu = self.menuBar().addMenu('Filters')
        self._processors_menu = self.menuBar().addMenu('Processors')

        # window menu
        windows_menu = self.menuBar().addMenu('Windows')
        cascade_action = windows_menu.addAction("Cascade")
        cascade_action.triggered.connect( lambda checked: self._mdi.cascadeSubWindows() )
        tile_action = windows_menu.addAction("Tile")
        tile_action.triggered.connect( lambda checked: self._mdi.tileSubWindows() )

        # add default filters and processors
        self.add_filter_widget( FileExtensionFilter() )
        self.add_filter_widget( FileOrFolderFilter() )
        self.add_processor_widget( FilePrinter() )
        self.add_processor_widget( FileStatisticsPrinter() )

        # finalize
        self.setCentralWidget(self._mdi)    
        self.setWindowTitle("File Essentials")       

    def filter_widget(self, name:str) -> Union[FilterWidget, None]:      
        #print(f'self._mdi.subWindowList(): {self._mdi.subWindowList()}')  
        for subwindow in self._mdi.subWindowList():
            widget = subwindow.widget()
            if isinstance(widget, FilterWidget) :        
                #print(f'widget.name(): {widget.name()}')  

                if widget.name() == name:
                    return widget            
        return None

    def processor_widget(self, name:str) -> Union[ProcessorWidget, None]:   
        for subwindow in self._mdi.subWindowList():
            widget = subwindow.widget()
            if isinstance(widget, ProcessorWidget) and widget.name() == name:
                return widget            
        return None

    def add_filter_widget( self, filter_widget:FilterWidget ) -> None:
        if self.filter_widget(filter_widget.name() ) != None:
            sys.stderr.write(f"Filter widget \"{filter_widget.name()}\" already added!\n")
            return

        # add subwindow
        subwindow = self._mdi.addSubWindow(filter_widget, QtCore.Qt.WindowMinMaxButtonsHint)
        subwindow.setWindowTitle(filter_widget.name())
        subwindow.hide()

        # add action
        action = self._filters_menu.addAction( filter_widget.name() )
        action.setObjectName( filter_widget.name() )
        action.triggered.connect( self._filter_action_clicked )
        action.setCheckable(True)

    def add_processor_widget( self, processor_widget:ProcessorWidget ) -> None:
        if self.processor_widget(processor_widget.name() ) != None:
            sys.stderr.write(f"Processor widget \"{processor_widget.name()}\" already added!\n")
            return

        # add subwindow
        subwindow = self._mdi.addSubWindow(processor_widget, QtCore.Qt.WindowMinMaxButtonsHint)
        subwindow.setWindowTitle(processor_widget.name())
        subwindow.hide()

        # add action
        action = self._processors_menu.addAction( processor_widget.name() )
        action.setObjectName( processor_widget.name() )
        action.triggered.connect( self._processor_action_clicked )
        action.setCheckable(True)

    def before_processing( self, base_directory:str ) -> None:
        for subwindow in self._mdi.subWindowList():
            widget = subwindow.widget()
            if isinstance(widget, FilterOrProcessorWidget):
                widget.before_processing(base_directory)

    def active_processor( self ) -> Union[None, ProcessorWidget]:        
        for curr_action in self._processors_menu.actions():
            if curr_action.isChecked():
                return self.processor_widget( curr_action.objectName() )
        return None

    def _filter_action_clicked( self, checked:bool ):
        # get sender and filter
        # get sender and processor
        action = self.sender()
        filter_widget_name = action.objectName()
        #print(f"Found action for processor {processor_name}")     
        filter = self.filter_widget(filter_widget_name)
        subwindow = filter.parent()                        
        subwindow.show() if checked else subwindow.hide()

    def _processor_action_clicked( self, checked:bool ):   
        # get sender and processor
        action = self.sender()
        processor_name = action.objectName()

        # hide all except current
        for subwindow in self._mdi.subWindowList():
            widget = subwindow.widget()
            if isinstance(widget, ProcessorWidget):                
                subwindow.show() if widget.name() == processor_name else subwindow.hide()

        # uncheck all actions
        for curr_action in self._processors_menu.actions():
            curr_action.setChecked(curr_action.text() == processor_name)

    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        active_filters:list[FilterWidget] = []
        for curr_action in self._filters_menu.actions():
            if curr_action.isChecked():
                active_filters.append( self.filter_widget( curr_action.objectName() ) )
        
        # check
        for filter in active_filters:
            if filter.use_file( abs_file_path, rel_file_path, level ) == False:
                return False
        return True
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    fes_main_window = FesMainWindow()
    fes_main_window.show()
    app.exec_()
