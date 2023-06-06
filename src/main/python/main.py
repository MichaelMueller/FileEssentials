# sys imports
import sys, os, datetime, abc, time, shutil
from typing import Union, Any, List, Dict

# pip imports
from filehash import FileHash
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSettings, QEvent
from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QListWidget, QFileDialog, QAbstractItemView, QMessageBox, QProgressDialog, QApplication, QLabel, QTextEdit, \
    QSplitter, QGroupBox, QMainWindow, QComboBox, QMdiArea, QMenu, QAction, QErrorMessage, QScrollArea, QButtonGroup, \
    QRadioButton, QSizePolicy, QMdiSubWindow, QSpinBox, QDoubleSpinBox
import pydicom

# module variables
fes_settings = QSettings(QSettings.UserScope, "https://github.com/MichaelMueller", "File Essentials")

# base classes            
class FesSubWindow(QMdiSubWindow):
    """ Each module is a subwindow """

    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        QMdiSubWindow.__init__(self, parent, flags)

    def main_window( self ) -> Union[None, "FesMainWindow"]:
        curr_object = self
        while curr_object is not None and not isinstance( curr_object, FesMainWindow ):
            curr_object = curr_object.parent()
        return curr_object

    def settings_value( self, name:str, default_value:Any=None ) -> Any:
        settings = fes_settings
        #settings.beginGroup(self.name())
        return settings.value( self.__class__.__name__+"."+str(name), default_value )

    def set_settings_value( self, name:str, value:Any ) -> None:
        settings = fes_settings
        #settings.beginGroup(self.name())
        settings.setValue( self.__class__.__name__+"."+str(name), value)
    
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        #print("Close Event!")
        a0.ignore()
        self.main_window().set_sub_window_visible( self, False )
        #return super().closeEvent(a0)
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
        self.main_window().set_base_directory(dir, True)

class FilePrinter(ProcessorSubWindow):
    def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
        ProcessorSubWindow.__init__(self, parent, flags)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel(self.description()))
        layout.addStretch()

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)        
                
    def description( self ) -> str:
        return "Prints the relative path and level for each file into the console"
    
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        self.main_window().console().append( f'{rel_file_path} (Level: {level})' )

    def before_processing( self ) -> None:
        self.main_window().console().reset()
        self.main_window().console().append("Items in directory <b>"+self.main_window().base_directory()+"</b>:")

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
        self._text_widget = QTextEdit()
        self._text_widget.setReadOnly( True )
        layout = QVBoxLayout()

        layout.addWidget(time_type_label)
        layout.addWidget(self._time_type)
        layout.addWidget(output_dir_path_label)
        layout.addWidget(self._output_dir_path)
        layout.addWidget(select_output_dir_path_button)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self._text_widget)

        widget = QWidget()
        widget.setLayout( layout )

        self.setWidget(widget)        

    def name( self ) -> str:
        return "ChronologicSorter"

    def description( self ) -> str:
        return "Sorts files in folders chronologically with its creation or modified date"
    
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        if not os.path.isfile( abs_file_path ):
            return
        output_dir_path = self._output_dir_path.text()
        if not output_dir_path:
            raise ValueError(f'{self.name()} - Please select an output directory!')
        if not os.path.isdir(output_dir_path):
            raise ValueError(f'{self.name()} - Not a valid output directory: "{output_dir_path}"!')
        
        file_stat = os.stat(abs_file_path)
        timestamp = file_stat.st_ctime if self._time_type.currentText() == "Change/Creation Time" else file_stat.st_mtime
        dt = datetime.datetime.fromtimestamp(timestamp)
        month_literal = self._months[ dt.month - 1 ]
        year_literal = str( dt.year )

        file_output_dir_path = os.path.abspath( output_dir_path + "/" + year_literal + "/" + month_literal )
        file_output_path = os.path.abspath( file_output_dir_path + "/" + os.path.basename( abs_file_path ) )
        #print( f'Would move {abs_file_path} to {file_output_path}')
        if not os.path.exists( file_output_dir_path ):
            self._text_widget.append(f'Creating directory <b>{file_output_dir_path}</b>')
            os.makedirs( file_output_dir_path, exist_ok= False )
        self._text_widget.append(f'Moving <b>{rel_file_path}</b> to <b>{file_output_path}</b>')
        shutil.move( abs_file_path, file_output_path )

    def before_processing(self, base_directory: str) -> None:
        self._text_widget.setHtml("")
        return super().before_processing(base_directory)

    def _select_output_dir_path(self):
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._output_dir_path.text() ) )
        if dir:
            dir = os.path.abspath( dir )
            self._output_dir_path.setText( dir )
        else:
            dir = ""
            self._output_dir_path.setText( "" )
        
        self.set_settings_value("output_dir_path", dir)

# class DeDuplicator(ProcessorSubWindow):
#     def __init__(self, parent=None):
#         ProcessorSubWindow.__init__(self, parent)

#         self._hasher = None
#         self._hashes:dict[str, list[str]] = {}
#         self._button_groups:dict[str, QButtonGroup] = {}

#         # self._text_widget = QTextEdit()
#         # self._text_widget.setReadOnly(True)

#         self._layout = QVBoxLayout()
#         # self._layout.addWidget( self._text_widget )
#         self._layout.addWidget(QLabel("Please process a directory first"))

#         self.setLayout(self._layout)

#     def name( self ) -> str:
#         return "DeDuplicator"

#     def description( self ) -> str:
#         return "Removes duplicates in the base directory"
    
#     def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
#         if os.path.isfile( abs_file_path ):
#             hash = self._hasher.hash_file(abs_file_path)
#             if not hash in self._hashes:
#                 self._hashes[hash] = []
#             self._hashes[hash].append( (abs_file_path, rel_file_path) )

#     def before_processing( self, base_directory:str ) -> None:
#         self._hasher = FileHash('md5')
#         self._hashes = {}
#         super().before_processing( base_directory )

#     def _clear_layout(self):
#         # clear layout
#         for i in reversed(range(self._layout.count())): 
#             child = self._layout.takeAt(i)
#             if child.widget():
#                 child.widget().deleteLater()

#     def post_processing(self) -> None:
#         self._clear_layout()

#         duplicates_selection_widget_layout = QVBoxLayout()
#         duplicates_selection_widget_layout.addWidget( QLabel(f'Duplicates in directory {self._base_directory}'))
#         self._button_groups:dict[str, QButtonGroup] = {}
#         # rebuild
#         for hash, hashed_files in self._hashes.items():
#             if len(hashed_files) > 1:
#                 #self._text_widget.append(f"Found duplicates: {hashed_files}")
#                 layout = QHBoxLayout()
#                 widget = QWidget()
#                 button_group = QButtonGroup( widget )
#                 self._button_groups[hash] = button_group

#                 for idx, path_tuple in enumerate(hashed_files):
#                     abs_file_path, rel_file_path = path_tuple
#                     print(abs_file_path)
#                     rad_button = QRadioButton(f"Keep {rel_file_path}")
#                     #rad_button.setChecked( idx + 1 == len(hashed_files) )
#                     rad_button.setChecked( idx == 0 )
#                     rad_button.setObjectName( rel_file_path )
#                     button_group.addButton( rad_button )

#                     file_layout = QVBoxLayout()
#                     _, file_ext = os.path.splitext( abs_file_path )
#                     #print(f'file: {file}')
#                     pixmap = None
#                     try:
#                         if file_ext.lower() in [".gif", ".jpeg", ".jpg", ".png", ".bmp"]:
#                             pixmap = QPixmap( abs_file_path )
#                     except:
#                         pass
#                     if pixmap is None:
#                         pixmap = QPixmap( os.path.abspath( os.path.dirname(__file__) + "/../icons/linux/128.png" ) )
#                     #pixmap = pixmap.scaledToWidth( 128 )
#                     #label = QLabel()
#                     #label.setPixmap( pixmap )
#                     label = PixmapLabel()
#                     label.setPixmap( pixmap )
#                     #label.setStyleSheet("width: 100%; height: auto;")
#                     #label.setScaledContents(True)
#                     file_layout.addWidget( label )
#                     file_layout.addWidget( rad_button )
#                     file_layout.addStretch()

#                     file_widget = QWidget()
#                     file_widget.setLayout( file_layout )

#                     layout.addWidget( file_widget )
#                     layout.setContentsMargins(0,0,0,0)
#                     layout.addStretch()

#                 widget.setLayout( layout )
#                 scroll_area = QScrollArea()
#                 scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#                 scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
#                 scroll_area.setWidgetResizable(True)
#                 scroll_area.setWidget(widget)
#                 scroll_area.setContentsMargins(0,0,0,0)
#                 scroll_area.setFrameStyle( Qt.FramelessWindowHint )
#                 duplicates_selection_widget_layout.addWidget( scroll_area )
        
#         backup_dir_path_label = QLabel("Backup Directory:")

#         self._backup_dir_path = QLineEdit()
#         self._backup_dir_path.setReadOnly(True)

#         select_backup_dir_path = QPushButton("Select")
#         select_backup_dir_path.clicked.connect(self.select_backup_dir_path)

#         self._remove_duplicates_button = QPushButton("Remove duplicates")
#         self._remove_duplicates_button.setDisabled( True )
#         self._remove_duplicates_button.clicked.connect(self.remove_duplicates)
        
#         backup_dir_path = self.settings_value("backup_dir_path")
#         if backup_dir_path and os.path.isdir( backup_dir_path ):
#             self._backup_dir_path.setText( backup_dir_path )
#             self._remove_duplicates_button.setDisabled( False )

#         duplicates_selection_widget_layout.addWidget( backup_dir_path_label )
#         duplicates_selection_widget_layout.addWidget( self._backup_dir_path )
#         duplicates_selection_widget_layout.addWidget( select_backup_dir_path )
#         duplicates_selection_widget_layout.addWidget( self._remove_duplicates_button )

#         #duplicates_selection_widget_layout.addStretch()
#         duplicates_selection_widget_layout.setContentsMargins(0,0,0,0)
#         duplicates_selection_widget = QWidget()
#         duplicates_selection_widget.setLayout( duplicates_selection_widget_layout )
#         duplicates_selection_widget_scroll_area = QScrollArea()
#         duplicates_selection_widget_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
#         duplicates_selection_widget_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
#         duplicates_selection_widget_scroll_area.setWidgetResizable( True )
#         duplicates_selection_widget_scroll_area.setWidget( duplicates_selection_widget )
#         duplicates_selection_widget_scroll_area.setContentsMargins(0,0,0,0)
#         duplicates_selection_widget_scroll_area.setFrameStyle( Qt.FramelessWindowHint )
#         self._layout.addWidget( duplicates_selection_widget_scroll_area )
#         parent:QWidget = self.parent()
        
#         QtCore.QTimer.singleShot(20, lambda: self.parent().adjustSize() if parent.width() < self._layout.sizeHint().width() or parent.height() < self._layout.sizeHint().height() else None )

#     def select_backup_dir_path(self):
#         dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._backup_dir_path.text() ) )
#         if dir:
#             dir = os.path.abspath( dir )
#             self.set_settings_value("backup_dir_path", dir)
#             self._backup_dir_path.setText( dir )
#             self._remove_duplicates_button.setEnabled( True )
#         else:
#             self._backup_dir_path.setText( "" )
#             self._remove_duplicates_button.setEnabled( False )
    
#     def remove_duplicates(self):
#         backup_dir = self._backup_dir_path.text()
#         for hash, button_group in self._button_groups.items():
#             rel_file_path_to_keep = button_group.checkedButton().objectName()
#             for path_tuple in self._hashes[hash]:
#                 abs_file_path, rel_file_path = path_tuple
#                 if rel_file_path == rel_file_path_to_keep:
#                     print(f'Would keep {rel_file_path}')
#                     continue
#                 else:
#                     target_path = os.path.abspath( backup_dir + "/" + rel_file_path )
#                     parent_backup_sub_dir = os.path.dirname( target_path )
#                     os.makedirs( parent_backup_sub_dir, exist_ok=True )
#                     print(f'Would move {abs_file_path} to {target_path}')
#                     shutil.move( abs_file_path, target_path )
#         self._clear_layout()
        
#         # self._layout.addWidget( self._text_widget )
#         self._layout.addWidget(QLabel("Please process a directory first"))
#         parent = self.parent()
#         QtCore.QTimer.singleShot(20, lambda: self.parent().adjustSize() if parent.width() < self._layout.sizeHint().width() or parent.height() < self._layout.sizeHint().height() else None )

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
        self.create_sub_window( FesConsoleSubWindow )
        self.create_sub_window( FesDirChooser )

        # add filters
        self.create_sub_window( BasicFilter )
        self.create_sub_window( DicomFilter )

        # add processor
        self.create_sub_window( FilePrinter )

        # finalize
        self.setCentralWidget(self._mdi)    
        self.setWindowTitle("File Essentials")  
        self.setWindowIcon( QIcon( os.path.abspath( os.path.dirname(__file__) + "/../icons/Icon.ico" ) ) )

        # restore
        maximized = fes_settings.value("maximized", False)
        #print(f'maximized: {maximized}')
        if maximized is True:
            self.setWindowState( Qt.WindowMaximized )

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
                                      
            #print(f'active_filter_names: {active_filter_names}')
            fes_settings.setValue(f'active_filters', active_filter_names)
        # save active processor (and disable the currently active)
        elif sub_window.sub_window_class() == ProcessorSubWindow:
            for action in menu.actions():
                if action.isChecked() and action.text() != sub_window.name():
                    self._set_sub_window_visible_by_class_and_name( ProcessorSubWindow, action.text(), False )
                    break
            
            active_processor_name = sub_window.name() if visible else None
            #print(f'active_processor_name: {active_processor_name}')
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
            active_processor.before_processing()

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
            active_processor.post_processing()
        progress_dialog.close()
        progress_dialog = None

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            #print(f'self.windowState() == Qt.WindowMaximized: {self.windowState() == Qt.WindowMaximized}')
            fes_settings.setValue("maximized", self.windowState() == Qt.WindowMaximized)

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
    #fes_settings.clear()
    
    app = QApplication(sys.argv)
    fes_main_window = FesMainWindow()
    fes_main_window.show()
    app.exec_()
