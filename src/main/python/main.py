# sys imports
import sys, os, datetime, abc, time, shutil
from typing import Union, Any, List, Dict

# pip imports
from fbs_runtime.application_context.PyQt5 import ApplicationContext
from filehash import FileHash
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSettings, QEvent
from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QListWidget, QFileDialog, QAbstractItemView, QMessageBox, QProgressDialog, QApplication, QLabel, QTextEdit, \
    QSplitter, QGroupBox, QMainWindow, QComboBox, QMdiArea, QMenu, QAction, QErrorMessage, QScrollArea, QButtonGroup, \
    QRadioButton, QSizePolicy, QMdiSubWindow, QSpinBox, QDoubleSpinBox, QCheckBox
import pydicom

# module variables
fes_settings = QSettings(QSettings.UserScope, "https://github.com/MichaelMueller", "File Essentials")

# functions
def validate_dir(dir:str, prefix:str):
    if not dir:
        raise ValueError(f'{prefix}Please select a directory!')
    if not os.path.isdir(dir):
        raise ValueError(f'{prefix}Not a valid directory: "{dir}"!')
  
# base classes            
class FesSubWindow(QMdiSubWindow):
    """ Each module is a subwindow """

    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        QMdiSubWindow.__init__(self, parent, flags)

    def try_restore_geometry(self):
               
        # restore state
        geometry:tuple = self.settings_value("geometry")
        #print(f'geometry in try_restore_geometry: {geometry}')
        if isinstance( geometry, tuple ):
            #pass
            self.setGeometry( *geometry )

    def main_window( self ) -> Union[None, "FesMainWindow"]:
        curr_object = self
        while curr_object is not None and not isinstance( curr_object, FesMainWindow ):
            curr_object = curr_object.parent()
        return curr_object

    def settings_value( self, name:str, default_value:Any=None ) -> Any:
        settings = fes_settings
        return settings.value( self.__class__.__name__+"."+str(name), default_value )

    def set_settings_value( self, name:str, value:Any ) -> None:
        settings = fes_settings
        settings.setValue( self.__class__.__name__+"."+str(name), value)
    
    def moveEvent(self, moveEvent: QtGui.QMoveEvent) -> None:
        #print(f'geometry in moveEvent: {self.geometry().getRect()}')
        self.set_settings_value("geometry", self.geometry().getRect())
        return super().moveEvent(moveEvent)

    def resizeEvent(self, resizeEvent: QtGui.QResizeEvent) -> None:
        #print(f'geometry in resizeEvent: {self.geometry().getRect()}')
        self.set_settings_value("geometry", self.geometry().getRect())
        return super().resizeEvent(resizeEvent)

    def changeEvent(self, event):        
        if event.type() == QEvent.WindowStateChange:
            #print(f"State changed {self.windowState()}")
            pass
        super().changeEvent(event)
        
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        a0.ignore()
        self.main_window().set_sub_window_visible( self, False )
        return
    
    def name( self ) -> str:
        return self.__class__.__name__

    def description( self ) -> str:
        return ""
    
    @abc.abstractclassmethod
    def sub_window_class( self ) -> type:
        raise NotImplementedError()

class BasicSubWindow(FesSubWindow):    
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        FesSubWindow.__init__(self, parent, flags)

    def sub_window_class( self ) -> type:
        return BasicSubWindow

class FilterSubWindow(FesSubWindow):    
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        FesSubWindow.__init__(self, parent, flags)

    def sub_window_class( self ) -> type:
        return FilterSubWindow
    
    @abc.abstractclassmethod
    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        raise NotImplementedError()
    
class ProcessorSubWindow(FesSubWindow):   
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        FesSubWindow.__init__(self, parent, flags)

    def sub_window_class( self ) -> type:
        return ProcessorSubWindow
    
    @abc.abstractclassmethod
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> None:
        raise NotImplementedError()    
    
    def before_processing( self ) -> None:
        """ Called each time BEFORE the processing of the directory starts """
        pass

    def post_processing( self ) -> None:
        """ Called each time AFTER the processing of the directory ended """
        pass

class FesConsoleSubWindow(BasicSubWindow):
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        BasicSubWindow.__init__(self, parent, flags)

        self._console_text_edit = QTextEdit()
        self._console_text_edit.setReadOnly( True )
        self._console_text_edit.setHtml("")

        widget_layout = QVBoxLayout()
        widget_layout.addWidget( self._console_text_edit )

        widget = QWidget()
        widget.setLayout( widget_layout )

        self.setWidget( widget )

    def name( self ) -> str:
        return "Console"
    
    def append( self, html_text:str ) -> "FesConsoleSubWindow":
        self._console_text_edit.append( html_text )

    def reset( self ) -> "FesConsoleSubWindow":
        self._console_text_edit.setHtml("")

class NotesSubWindow(BasicSubWindow):
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        BasicSubWindow.__init__(self, parent, flags)

        self._text_edit = QTextEdit()
        self._text_edit.textChanged.connect( lambda: self.set_settings_value("text", self._text_edit.toPlainText()) )
        self._text_edit.setText( self.settings_value("text", "") )

        widget_layout = QVBoxLayout()
        widget_layout.addWidget( self._text_edit )

        widget = QWidget()
        widget.setLayout( widget_layout )

        self.setWidget( widget )

    def name( self ) -> str:
        return "Notes"

class FesDirChooser(BasicSubWindow):
    """ The fundamental widget for choosing the base directory """
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        BasicSubWindow.__init__(self, parent, flags)

        # build UI
        self._base_directory = QLineEdit()
        self._base_directory.setReadOnly(True)
        self._base_directory.setStyleSheet("min-width: 240px;")
        self._base_directory.setText(fes_settings.value("base_directory", ""))

        select_directory_button = QPushButton("Select Directory")
        select_directory_button.clicked.connect(self.select_directory_button_clicked)

        self._process_button = QPushButton("Process directory")
        self._process_button.clicked.connect(self.process_button_clicked)
        self._process_button.setDisabled(self._base_directory.text() == "")

        error_timeout = QDoubleSpinBox()
        error_timeout.setMinimum(0.0)
        error_timeout.setValue( float( fes_settings.value("error_timeout", 0.5) ) )
        error_timeout.valueChanged.connect( lambda changed_value: self.main_window().set_error_timeout( changed_value ) )

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Timeout on error [sec]:"))
        layout.addWidget(error_timeout)
        layout.addWidget(QLabel("Base Directory:"))
        layout.addWidget(self._base_directory)
        layout.addWidget(select_directory_button)
        layout.addWidget(self._process_button)
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)
   
    def name( self ) -> str:
        return "Basic Settings"
    
    def process_button_clicked(self):
        self.main_window().start_processing()

    def select_directory_button_clicked(self):
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._base_directory.text() ) )
        self._base_directory.setText(dir)
        self._process_button.setDisabled(self._base_directory.text() == "")
        self.main_window().set_base_directory(dir, False)

class FilePrinter(ProcessorSubWindow):
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        ProcessorSubWindow.__init__(self, parent, flags)
        
        self._num_dirs = 0
        self._num_files = 0

        layout = QVBoxLayout()
        layout.addWidget(QLabel(self.description()))
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)        
                
    def description( self ) -> str:
        return "Prints the relative path and level for each file into the console"
    
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        if os.path.isdir( abs_file_path ):
            prefix = "Directory"
            self._num_dirs += 1
        elif os.path.isfile( abs_file_path ):
            prefix = "File"
            self._num_files += 1
        self.main_window().console().append( f'{prefix} {rel_file_path} at level {level})' )

    def before_processing( self ) -> None:
        self._num_dirs = 0
        self._num_files = 0
        self.main_window().console().reset()
        self.main_window().console().append("Items in directory <b>"+self.main_window().base_directory()+"</b>:")

    def post_processing( self ) -> None:
        self.main_window().console().append(f"Overall statistics for directory <b>"+self.main_window().base_directory()+"</b>:")
        self.main_window().console().append(f"{self._num_dirs+self._num_files} items found")
        self.main_window().console().append(f"{self._num_dirs} directories found")
        self.main_window().console().append(f"{self._num_files} files found")

class ChronologicSorter(ProcessorSubWindow):
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        ProcessorSubWindow.__init__(self, parent, flags)

        # internal state
        self._months = [ "01_Jan", "02_Feb", "03_Mar", "04_Apr", "05_May", "06_Jun", "07_Jul", "08_Aug", "09_Sep", "10_Oct", "11_Nov", "12_Dec" ]

        # build widgets
        time_type_label = QLabel("Select the relevant time file attribute:")
        self._time_type = QComboBox()
        self._time_type.addItem("Change/Creation Time")
        self._time_type.addItem("Modification Time")
        output_dir_path_label = QLabel("Output Directory:")
        self._output_dir_path = QLineEdit()
        self._output_dir_path.setReadOnly(True)
        self._output_dir_path.setStyleSheet("min-width: 240px")
        self._output_dir_path.setText( self.settings_value("output_dir_path") )
        select_output_dir_path_button = QPushButton("Change")
        select_output_dir_path_button.clicked.connect(self._select_output_dir_path)
        file_action = QComboBox()
        file_action.addItem("Move files")
        file_action.addItem("Copy files")
        file_action.setCurrentText( self.settings_value("file_action", "Move files") )
        file_action.currentTextChanged.connect( lambda changed_text: self.set_settings_value("file_action", changed_text) )
        layout = QVBoxLayout()

        layout.addWidget(time_type_label)
        layout.addWidget(self._time_type)
        layout.addWidget(QLabel("Select the appropriate action: "))
        layout.addWidget(file_action)
        layout.addWidget(output_dir_path_label)
        layout.addWidget(self._output_dir_path)
        layout.addWidget(select_output_dir_path_button)
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)        

    def name( self ) -> str:
        return "ChronologicSorter"

    def description( self ) -> str:
        return "Sorts files in folders chronologically with its creation or modified date"
    
    def before_processing( self ) -> None:
        self.main_window().console().reset()

    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        if not os.path.isfile( abs_file_path ):
            return
        validate_dir( self._output_dir_path.text(), self.name() )
        output_dir_path = self._output_dir_path.text()
        
        file_stat = os.stat(abs_file_path)
        timestamp = file_stat.st_ctime if self._time_type.currentText() == "Change/Creation Time" else file_stat.st_mtime
        dt = datetime.datetime.fromtimestamp(timestamp)
        month_literal = self._months[ dt.month - 1 ]
        year_literal = str( dt.year )

        file_output_dir_path = os.path.abspath( output_dir_path + "/" + year_literal + "/" + month_literal )
        file_output_path = os.path.abspath( file_output_dir_path + "/" + os.path.basename( abs_file_path ) )
        # i = 1
        # while os.path.exists(file_output_path):
        #     i += 1
        #     file_name, ext = os.path.splitext(file_output_path)
        #     file_output_path = file_name + f"_{i}" + ext
        #print( f'Would move {abs_file_path} to {file_output_path}')
        if not os.path.exists( file_output_dir_path ):
            self.main_window().console().append(f'Creating directory <b>{file_output_dir_path}</b>')
            os.makedirs( file_output_dir_path, exist_ok= False )
        file_action = self.settings_value("file_action", "Move files")
        self.main_window().console().append(f'{"Moving" if file_action == "Move files" else "Copying"} <b>{rel_file_path}</b> to <b>{file_output_path}</b>')
        shutil.move( abs_file_path, file_output_path ) if file_action == "Move files" else shutil.copy( abs_file_path, file_output_path )

    def _select_output_dir_path(self):
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._output_dir_path.text() ) )
        if dir:
            dir = os.path.abspath( dir )
            self._output_dir_path.setText( dir )
        else:
            dir = ""
            self._output_dir_path.setText( "" )
        
        self.set_settings_value("output_dir_path", dir)

class DirectoryComparer(ProcessorSubWindow):
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        ProcessorSubWindow.__init__(self, parent, flags)

        # internal state
        self._num_dirs_missing = 0
        self._num_files_missing = 0

        # build widgets
        target_dir_path_label = QLabel("Target Directory:")
        self._target_dir_path = QLineEdit()
        self._target_dir_path.setReadOnly(True)
        self._target_dir_path.setStyleSheet("min-width: 240px")
        self._target_dir_path.setText( self.settings_value("target_dir_path") )
        select_target_dir_path_button = QPushButton("Change")
        select_target_dir_path_button.clicked.connect(self._select_target_dir_path)
        layout = QVBoxLayout()

        layout.addWidget(target_dir_path_label)
        layout.addWidget(self._target_dir_path)
        layout.addWidget(select_target_dir_path_button)
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)        

    def name( self ) -> str:
        return "DirectoryComparer"

    def description( self ) -> str:
        return "Compares the base directory with the target directory for missing files and/or directories"
    
    def before_processing( self ) -> None:    
        self._num_dirs_missing = 0
        self._num_files_missing = 0    
        self.main_window().console().reset()

        validate_dir( self._target_dir_path.text(), self.name() )
        self.main_window().console().append(f"Missing files and directories in {self._target_dir_path.text()}")

    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        validate_dir( self._target_dir_path.text(), self.name() )

        target_dir_path = self._target_dir_path.text()
        abs_file_path_in_target_dir = os.path.abspath( target_dir_path + "/" + rel_file_path )

        if not os.path.exists( abs_file_path_in_target_dir ):
            if os.path.isdir( abs_file_path ):
                type_ = "directory"
                self._num_dirs_missing += 1
            elif os.path.isfile( abs_file_path ):
                type_ = "file"
                self._num_files_missing += 1
            self.main_window().console().append(f'Missing {type_} "{rel_file_path}"')

    def _select_target_dir_path(self):
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._target_dir_path.text() ) )
        if dir:
            dir = os.path.abspath( dir )
            self._target_dir_path.setText( dir )
        else:
            dir = ""
            self._target_dir_path.setText( "" )
        
        self.set_settings_value("target_dir_path", dir)
        
    def post_processing( self ) -> None:
        validate_dir( self._target_dir_path.text(), self.name() )
        
        self.main_window().console().append(f"Overall missing statistics for directory <b>"+self._target_dir_path.text()+"</b> compared to <b>"+self.main_window().base_directory()+"</b>:")
        self.main_window().console().append(f"{self._num_dirs_missing+self._num_files_missing} items mssing")
        self.main_window().console().append(f"{self._num_dirs_missing} directories missing")
        self.main_window().console().append(f"{self._num_files_missing} files missing")

class Deduplicator(ProcessorSubWindow):
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        ProcessorSubWindow.__init__(self, parent, flags)

        # internal state
        self._hasher:FileHash = None
        self._hashes:dict[str, str] = {}
        self._total_files = 0
        self._files_removed = 0

        # build widgets
        self._dry_run = QCheckBox("Dry run")
        self._dry_run.setChecked(True)

        self._hash_method = QComboBox()
        self._hash_method.addItem("md5")
        self._hash_method.addItem("sha1")    
        self._hash_method.currentTextChanged.connect( lambda changed_text: self.set_settings_value("hash_method", changed_text) )
        self._hash_method.setCurrentText( self.settings_value( "hash_method", "md5" ) )

        self._backup_dir_path = QLineEdit()
        self._backup_dir_path.setReadOnly(True)
        self._backup_dir_path.setStyleSheet("min-width: 240px")
        self._backup_dir_path.setText( self.settings_value("backup_dir_path") )
        select_backup_dir_path_button = QPushButton("Change")
        select_backup_dir_path_button.clicked.connect(self._select_backup_dir_path)

        layout = QVBoxLayout()
        layout.addWidget( QLabel( self.description() ) )
        layout.addWidget( self._dry_run )
        layout.addWidget( QLabel("Hashing algorithm") )
        layout.addWidget( self._hash_method )
        layout.addWidget( QLabel("Backup Directory:") )
        layout.addWidget( self._backup_dir_path )
        layout.addWidget( select_backup_dir_path_button )
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)        

    def _select_backup_dir_path(self):
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._backup_dir_path.text() ) )
        if dir:
            dir = os.path.abspath( dir )
            self._backup_dir_path.setText( dir )
        else:
            dir = ""
            self._backup_dir_path.setText( "" )
        
        self.set_settings_value("backup_dir_path", dir)

    def description( self ) -> str:
        return "Removes duplicate files from a directory"
    
    def before_processing( self ) -> None:
        self._hasher = FileHash(self._hash_method.currentText())
        self._hashes = {}
        self._total_files = 0
        self._files_removed = 0
        self.main_window().console().reset()
        self.main_window().console().append(f'Removing duplicates in directory <b>{self.main_window().base_directory()}</b>')

    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        if os.path.isfile( abs_file_path ):
            hash = self._hasher.hash_file(abs_file_path)
            self._total_files += 1
            if hash in self._hashes:              
                self._files_removed += 1
                dry_run = self._dry_run.isChecked()
                prefix = "[DRY RUN] Would remove" if dry_run else "Removing"
                self.main_window().console().append(f'{prefix} duplicate file <b>{rel_file_path}</b> with hash {hash}')

                # make backup
                backup_dir = self._backup_dir_path.text()
                if os.path.isdir( backup_dir ):
                    first_file_abs_path = self._hashes[hash]
                    _, first_file_ext = os.path.splitext(first_file_abs_path)
                    backup_first_file = os.path.abspath( backup_dir + "/" + hash + "_0" + first_file_ext )
                    if not os.path.exists(backup_first_file):
                        self.main_window().console().append(f'Copying first file from {first_file_abs_path} to {backup_first_file}')
                        shutil.copy( first_file_abs_path, backup_first_file )

                    i = 1
                    _, ext = os.path.splitext(abs_file_path)
                    while True:
                        backup_file_path = os.path.abspath( backup_dir + "/" + hash + "_" + str(i) + ext )
                        if not os.path.exists( backup_file_path ):
                            break
                        i += 1
                    self.main_window().console().append(f'Copying duplicate file from {rel_file_path} to {backup_file_path}')
                    shutil.copy( abs_file_path, backup_file_path )

                if dry_run is False:
                    os.remove( abs_file_path )
            else:
                self._hashes[hash] = abs_file_path
    
    def post_processing(self) -> None:
        dry_run = self._dry_run.isChecked()
        prefix = "[DRY RUN] Would have removed" if dry_run else "Removed"
        self.main_window().console().append(f'In directory {self.main_window().base_directory()}: {prefix} {self._files_removed} duplicates out of {self._total_files} files')
        self._dry_run.setChecked(True)
      
class DicomFilter(FilterSubWindow):
    
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        FilterSubWindow.__init__(self, parent, flags)

        layout = QVBoxLayout()
        layout.addWidget( QLabel(self.description()) )
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)

    def description( self ) -> str:
        return "Checks for valid DICOM files"
    
    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        if not os.path.isfile( abs_file_path ):
            return False        
        try:
            return pydicom.misc.is_dicom(abs_file_path)
        except pydicom.errors.InvalidDicomError:
            return False
        
class BasicFilter(FilterSubWindow):
    
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        FilterSubWindow.__init__(self, parent, flags)

        choice_label = QLabel("Select target file items:")
        self._choice = QComboBox()
        self._choice.addItem("Files and Folders")
        self._choice.addItem("Only Files")
        self._choice.addItem("Only Folders")
        self._choice.setStyleSheet("min-width: 240px;")
        self._choice.currentTextChanged.connect( lambda changed_text: self.set_settings_value("choice", changed_text) )
        self._choice.setCurrentText( self.settings_value( "choice", "Files and Folders" ) )

        extensions_label = QLabel("Enter allowed extensions (e.g. \"*.jpg; *.txt\")")
        self._extensions_input = QLineEdit()
        self._extensions_input.textChanged.connect( lambda changed_text: self.set_settings_value("extensions", changed_text) )
        self._extensions_input.setText( self.settings_value( "allowed_extensions", "*.*" ) )

        maximum_recursion_level_label = QLabel("Maximum recursion level:")
        self._maximum_recursion_level = QSpinBox()
        self._maximum_recursion_level.setMinimum(-1)
        self._maximum_recursion_level.setValue( self.settings_value( "maximum_recursion_level", -1 ) )
        self._maximum_recursion_level.valueChanged.connect( lambda new_value: self.set_settings_value("maximum_recursion_level", new_value) )

        layout = QVBoxLayout()
        layout.addWidget( choice_label )
        layout.addWidget( self._choice )
        layout.addWidget( extensions_label )
        layout.addWidget( self._extensions_input )
        layout.addWidget( maximum_recursion_level_label )
        layout.addWidget( self._maximum_recursion_level )
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)

    def description( self ) -> str:
        return "Exposes some basic filtering options"
    
    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:       
        if self._choice.currentText() == "Files and Folders":
            valid = True
        elif self._choice.currentText() == "Only Folders":
            valid = os.path.isdir( abs_file_path )
        elif self._choice.currentText() == "Only Files":
            valid = os.path.isfile( abs_file_path )

        if valid:        
            maximum_recursion_level = self.settings_value( "maximum_recursion_level", -1 )
            if maximum_recursion_level > -1 and level > maximum_recursion_level:
                valid = False

        if valid and os.path.isfile( abs_file_path ):
            allowed_file_extensions:list[str] = self.settings_value( "allowed_extensions", "*.*" ).split(";")
            if len( allowed_file_extensions ) > 0:
                allowed_file_extensions = [ allowed_file_extension.strip().replace("*.", ".").lower() for allowed_file_extension in allowed_file_extensions ]        
                _, file_ext = os.path.splitext(abs_file_path)
                valid = file_ext.lower() in allowed_file_extensions or ".*" in allowed_file_extensions       


        return valid


class FesMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # build widgets
        self._mdi = QMdiArea()
        self._mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # filter and processor menus
        self._basic_tools_menu = self.menuBar().addMenu('Basic Tools')
        self._filters_menu = self.menuBar().addMenu('Filters')
        self._filters_separator = self._filters_menu.addSeparator()
        self._uncheck_all_action = self._filters_menu.addAction( "Uncheck all" )
        self._uncheck_all_action.triggered.connect( self._deactivate_all_filters )
        self._processors_menu = self.menuBar().addMenu('Processors')

        # window arrangement menu
        windows_menu = self.menuBar().addMenu('Arrange Windows')
        cascade_action = windows_menu.addAction("Cascade")
        cascade_action.triggered.connect( lambda checked: self._mdi.cascadeSubWindows() )
        tile_action = windows_menu.addAction("Tile")
        tile_action.triggered.connect( lambda checked: self._mdi.tileSubWindows() )

        # add basic subwindows
        self.create_sub_window( NotesSubWindow )
        self.create_sub_window( FesConsoleSubWindow )
        self.create_sub_window( FesDirChooser )

        # add filters
        self.create_sub_window( DicomFilter )
        self.create_sub_window( BasicFilter )

        # add processor
        self.create_sub_window( FilePrinter )
        self.create_sub_window( ChronologicSorter )
        self.create_sub_window( DirectoryComparer )
        self.create_sub_window( Deduplicator )

        # finalize
        self.setCentralWidget(self._mdi)    
        self.setWindowTitle("File Essentials")  
        self.setWindowIcon( QIcon( os.path.abspath( os.path.dirname(__file__) + "/../icons/Icon.ico" ) ) )

        # restore        
        geometry = fes_settings.value("geometry", None)
        #print(f'geometry: {geometry}')
        if isinstance(geometry, QtCore.QByteArray):
            #print("Restore geometry")
            self.restoreGeometry(geometry)
        window_state = fes_settings.value("window_state", None)
        if isinstance(window_state, QtCore.QByteArray):
            self.restoreState(window_state)

        # maximized = fes_settings.value("maximized", False)
        # #print(f'maximized in ctor: {maximized}')
        # if maximized is not False:
        #     #print(f'maximized in ctor 2: {maximized}')
        #     self.setWindowState( Qt.WindowMaximized )

    def create_sub_window(self, class_:type):
        # assert correct class before creation
        if not issubclass( class_, FesSubWindow ):
            sys.stderr.write(f'{class_.__name__} is not a subclass of {FesSubWindow.__name__}\n')
            return
        sub_window:FesSubWindow = class_()

        # assert the window was not created before adding it
        sub_window_class = sub_window.sub_window_class()
        if self._sub_window_by_class_and_name( sub_window_class, sub_window.name() ) != None:            
            sys.stderr.write(f'{sub_window_class.__name__} "{sub_window.name()}" already created!\n')
            return            
        sub_window.setWindowTitle( sub_window.name() )
        self._mdi.addSubWindow( sub_window )
        sub_window.try_restore_geometry()

        # build the action in the corresponding menu
        action = QAction(self)
        action.setText( sub_window.name() )
        action.setObjectName( sub_window.name() )
        action.setCheckable(True)
        action.setToolTip( sub_window.description() )
        action.triggered.connect( lambda checked: self.set_sub_window_visible( sub_window, checked ) )
        # add to the menu
        menu:QMenu = self._menu_by_class( sub_window )
        existing_actions = menu.actions()
        if len(existing_actions) > 0:
            menu.insertAction( existing_actions[0], action )
        else:
            menu.addAction( action )

        # restore the state
        if sub_window_class == BasicSubWindow:
            sub_window_visible = True

        elif sub_window_class == FilterSubWindow:
            active_filters = fes_settings.value(f'active_filters', [])
            #print(f'active_filters: {active_filters}')
            sub_window_visible = sub_window.name() in active_filters

        elif sub_window_class == ProcessorSubWindow:
            active_processor_name = fes_settings.value(f'active_processor', None)
            #print(f'active_processor: {active_processor_name}')
            sub_window_visible = sub_window.name() == active_processor_name

        self.set_sub_window_visible( sub_window, sub_window_visible )

    def set_sub_window_visible( self, sub_window:FesSubWindow, visible:bool ):
        menu:QMenu = self._menu_by_class( sub_window )

        # save the state of visible windows for next time
        # save active filters
        if sub_window.sub_window_class() == FilterSubWindow:
            active_filter_names:list[str] = fes_settings.value(f'active_filters', [])

            if sub_window.name() in active_filter_names:
                active_filter_names.remove( sub_window.name() )

            if visible:
                active_filter_names.append( sub_window.name() )  
                                      
            #print(f'active_filters: {active_filter_names}')
            fes_settings.setValue(f'active_filters', active_filter_names)

        # save active processor (and disable the currently active)
        elif sub_window.sub_window_class() == ProcessorSubWindow and visible:
            active_processor_name = fes_settings.value(f'active_processor', None)
            if active_processor_name is not None and active_processor_name != sub_window.name():
                self._set_sub_window_visible_by_class_and_name( ProcessorSubWindow, active_processor_name, False )
                                
            active_processor_name = sub_window.name() if visible else None
            #print(f'active_processor: {active_processor_name}')
            fes_settings.setValue(f'active_processor', active_processor_name)

        # apply the state
        sub_window.show() if visible else sub_window.hide()
        for action in menu.actions():            
            if action.text() == sub_window.name():
                action.setChecked(visible)
                break            
        
        if sub_window.sub_window_class() == FilterSubWindow:
            active_filter_names:list[str] = fes_settings.value(f'active_filters', [])
            for action in menu.actions():
                filter_name = action.objectName()
                if not filter_name:
                    continue
                if filter_name in active_filter_names:
                    index = active_filter_names.index( filter_name )
                    action.setText( f'{index+1}: { filter_name }')
                else:
                    action.setText( filter_name )

    def base_directory( self ) -> Union[str, None]:
        return fes_settings.value("base_directory", None)

    def set_base_directory( self, base_directory:Union[str,None], start_processing:bool=True ) -> None:        
        if base_directory:
            if not os.path.isdir( base_directory ):
                error_dialog = QErrorMessage()
                error_dialog.setWindowTitle( "Error" )
                error_dialog.setModal(True)
                error_dialog.showMessage(f'Not a directory: "{base_directory}"')
                return
            base_directory = os.path.abspath( base_directory )
            fes_settings.setValue( "base_directory", base_directory )
            if start_processing:
                self.start_processing()                

    def error_timeout( self ) -> float:
        return float( fes_settings.value("error_timeout", 0.5) )

    def set_error_timeout( self, error_timeout:float ) -> None:        
        fes_settings.setValue( "error_timeout", float(error_timeout) )

    def console( self ) -> FesConsoleSubWindow:
        return self._sub_window_by_class_and_name( BasicSubWindow, "Console" )

    def start_processing(self):
        # base_directory error handling
        base_directory = fes_settings.value("base_directory")
        base_directory = os.path.abspath( base_directory )
        error = None
        if base_directory == "":
            error = f'Please choose a base directory first'
        elif not os.path.isdir( base_directory ):
            error = f'Not a directory: "{base_directory}"'

        if error:
            error_dialog = QErrorMessage()
            error_dialog.setWindowTitle("Error")
            error_dialog.setWindowModality(Qt.WindowModal)
            error_dialog.showMessage(error)
            return

        # setup progress dialog
        progress_dialog = QProgressDialog("Processing ...", "Cancel", 0, 0, self)
        progress_dialog.setWindowTitle("File Essentials - Processing")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setStyleSheet("min-width: 640px;")
        progress_dialog.setAutoReset(True)
        progress_dialog.setAutoClose(False)
        progress_dialog.show()

        # collect files
        i = 0
        file_infos:list[tuple[str, str, int]] = []
        progress_dialog.setLabelText("Collecting files")
        for root, dirnames, filenames in os.walk(base_directory):     
            if progress_dialog.wasCanceled():
                return
            else:
                level = root[len(base_directory):].count(os.sep)
                for basename in dirnames + filenames:
                    abs_path = os.path.join(root, basename)
                    rel_path = abs_path.replace( base_directory, "" )
                    rel_path = rel_path.replace( "\\", "/" )[1:]
                    file_infos.append( (abs_path, rel_path, level) )
                        
                i = i + 1 if i < 100 else 0
                progress_dialog.setValue(i)
            QApplication.processEvents()
            

        # process files
        progress_dialog.setLabelText("Processing files")
        progress_dialog.setValue(0)
        progress_dialog.setRange(0, len(file_infos))

        # get active filters
        active_filter_names:list[str] = fes_settings.value(f'active_filters', [])
        active_filters:list[FilterSubWindow] = [ self._sub_window_by_class_and_name(FilterSubWindow, active_filter_name) for active_filter_name in active_filter_names]

        # get active processor
        active_processor_name = fes_settings.value(f'active_processor', None)        
        active_processor:ProcessorSubWindow = self._sub_window_by_class_and_name( ProcessorSubWindow, active_processor_name )
        
        if active_processor:
            try:                    
                active_processor.before_processing()
            except Exception as e:                
                progress_dialog.setLabelText(f'Error: {e}')
                time.sleep(self.error_timeout())

        for i, file_info in enumerate(file_infos):            
            if progress_dialog.wasCanceled():
                break
            else:
                try:                    
                    progress_dialog.setLabelText(f'Processing {file_info[1]}')
                    
                    # check with filters for usage
                    use_file = True
                    for filter in active_filters:
                        if filter.use_file( file_info[0], file_info[1], file_info[2] ) is False:
                            use_file = False
                            break
                    
                    if use_file and active_processor:
                        active_processor.process( file_info[0], file_info[1], file_info[2] )
                except Exception as e:                
                    progress_dialog.setLabelText(f'Error: {e}')
                    # wait on errors #TODO make configurable?
                    time.sleep(self.error_timeout())

                progress_dialog.setValue( i )
            QApplication.processEvents()

        if active_processor:
            try:                    
                active_processor.post_processing()
            except Exception as e:                
                progress_dialog.setLabelText(f'Error: {e}')
                time.sleep(self.error_timeout())
        progress_dialog.close()
        progress_dialog = None

    def changeEvent(self, event):        
        if event.type() == QEvent.WindowStateChange:
            fes_settings.setValue("window_state", self.saveState())
        super().changeEvent(event)

    def moveEvent(self, moveEvent: QtGui.QMoveEvent) -> None:
        fes_settings.setValue("geometry", self.saveGeometry())
        super().moveEvent(moveEvent)

    def resizeEvent(self, resizeEvent: QtGui.QResizeEvent) -> None:
        fes_settings.setValue("geometry", self.saveGeometry())
        super().resizeEvent(resizeEvent)
    
    # def closeEvent(self, event):
    #     #print("Closing...")
    #     geometry = self.saveGeometry()
    #     #print(f'geometry in close event: {geometry}')
    #     fes_settings.setValue("geometry", geometry)
    #     fes_settings.setValue("window_state", self.saveState())
    #     fes_settings.sync()
    #     super().closeEvent(event)

    def _menu_by_class( self, sub_window:FesSubWindow ):
        menus_by_class = { BasicSubWindow: self._basic_tools_menu, FilterSubWindow: self._filters_menu, ProcessorSubWindow: self._processors_menu }
        return menus_by_class[sub_window.sub_window_class()]
    
    def _set_sub_window_visible_by_class_and_name( self, class_:type, name:str, visible:bool ):
        self.set_sub_window_visible(self._sub_window_by_class_and_name(class_, name), visible)

    def _sub_window_by_class_and_name( self, class_:type, name:str ) -> Union[None, FesSubWindow]:        
        for sub_window in self._sub_windows_by_class( class_ ):
            if sub_window.name() == name:
                return sub_window
        return None

    def _sub_windows_by_class( self, class_:type ) -> List[FesSubWindow]:
        sub_windows = []
        for sub_window in self._mdi.subWindowList():
            if isinstance( sub_window, FesSubWindow ) and isinstance( sub_window, class_ ):
                sub_windows.append( sub_window )
        return sub_windows

    def _deactivate_all_filters(self, checked:bool=False):
        active_filters:list[str] = fes_settings.value("active_filters", [])
        for filter_name in active_filters:
            self._set_sub_window_visible_by_class_and_name( FilterSubWindow, filter_name, False )
        
if __name__ == '__main__':
    # fes_settings.clear()

    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    fes_main_window = FesMainWindow()
    fes_main_window.show()
    exit_code = appctxt.app.exec()      # 2. Invoke appctxt.app.exec()
    sys.exit(exit_code)
    
