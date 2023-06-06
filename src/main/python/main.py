# sys imports
import sys, os, datetime, abc, time, shutil
from typing import Union, Any

# pip imports
from filehash import FileHash
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSettings, QEvent
from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QListWidget, QFileDialog, QAbstractItemView, QMessageBox, QProgressDialog, QApplication, QLabel, QTextEdit, \
    QSplitter, QGroupBox, QMainWindow, QComboBox, QMdiArea, QMenu, QAction, QErrorMessage, QScrollArea, QButtonGroup, \
    QRadioButton, QSizePolicy

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

    def post_processing( self ) -> None:
        pass

    def settings_value( self, name:str, default_value:Any=None ) -> Any:
        settings = FesWidget.global_settings()
        #settings.beginGroup(self.name())
        return settings.value( self.__class__.__name__+"."+str(name), default_value )

    def set_settings_value( self, name:str, value:Any ) -> None:
        settings = FesWidget.global_settings()
        #settings.beginGroup(self.name())
        settings.setValue( self.__class__.__name__+"."+str(name), value)
    
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
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._base_directory.text() ) )
        self.set_base_directory(dir, True)

    def _start_processing(self):
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
                rel_path = rel_path.replace( "\\", "/" )[1:]
                file_infos.append( (abs_path, rel_path, level) )
                     
            i = i + 1 if i < 100 else 0
            progress_dialog.setValue(i)
        #print(f'file_infos: {file_infos}')  

        # process files
        progress_dialog.setLabelText("Processing files")
        progress_dialog.setValue(0)
        progress_dialog.setRange(0, len(file_infos))
        main_window = self.main_window()
        main_window.before_processing( base_directory_abs_path )
        processor_widget = main_window.active_processor()

        for i, file_info in enumerate(file_infos):            
            if progress_dialog.wasCanceled():
                break
            QApplication.processEvents()

            # TODO try catch
            try:
                
                progress_dialog.setLabelText(f'Processing {file_info[1]}')
                if main_window.use_file( file_info[0], file_info[1], file_info[2] ):
                    if processor_widget:
                        processor_widget.process( file_info[0], file_info[1], file_info[2] )
            except Exception as e:                
                progress_dialog.setLabelText(f'Error: {e}')
                time.sleep(0.5)
                #error = str(e)
                #QtCore.QTimer.singleShot(2000, lambda: print(error) )

            progress_dialog.setValue( i )

        main_window.post_processing()
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
    
class PixmapLabel(QLabel):
    def __init__(self, parent=None):
        QLabel.__init__(self, parent)
        self.setMinimumSize(1,1)
        self.setScaledContents(False)

        self._pixmap:QPixmap = None

    def setPixmap ( self, p:QPixmap ) -> None:
        self._pixmap = p;
        super().setPixmap( self._scaled_pixmap() )

    def _scaled_pixmap(self) -> QPixmap:
        return self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def heightForWidth( self, width:int ) -> int:
        return self.height() if self._pixmap.isNull() else float(self._pixmap.height()*width)/self._pixmap.width()

    def sizeHint(self) -> QtCore.QSize:
        w = self.width()
        return QtCore.QSize( w, self.heightForWidth(w) )
    
    def resizeEvent(self, e: QtGui.QResizeEvent ) -> None:
        if self._pixmap.isNull() == False:
            super().setPixmap(self._scaled_pixmap())

class DeDuplicator(ProcessorWidget):
    def __init__(self, parent=None):
        ProcessorWidget.__init__(self, parent)

        self._hasher = None
        self._hashes:dict[str, list[str]] = {}
        self._button_groups:dict[str, QButtonGroup] = {}

        # self._text_widget = QTextEdit()
        # self._text_widget.setReadOnly(True)

        self._layout = QVBoxLayout()
        # self._layout.addWidget( self._text_widget )
        self._layout.addWidget(QLabel("Please process a directory first"))

        self.setLayout(self._layout)

    def name( self ) -> str:
        return "DeDuplicator"

    def description( self ) -> str:
        return "Removes duplicates in the base directory"
    
    def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        if os.path.isfile( abs_file_path ):
            hash = self._hasher.hash_file(abs_file_path)
            if not hash in self._hashes:
                self._hashes[hash] = []
            self._hashes[hash].append( rel_file_path )

    def before_processing( self, base_directory:str ) -> None:
        self._hasher = FileHash('md5')
        self._hashes = {}
        #self._text_widget.setHtml("")
        super().before_processing( base_directory )

    def _clear_layout(self):
        # clear layout
        for i in reversed(range(self._layout.count())): 
            child = self._layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()

    def post_processing(self) -> None:
        self._clear_layout()

        duplicates_selection_widget_layout = QVBoxLayout()
        duplicates_selection_widget_layout.addWidget( QLabel(f'Duplicates in directory {self._base_directory}'))
        self._button_groups:dict[str, QButtonGroup] = {}
        # rebuild
        for hash, hashed_files in self._hashes.items():
            if len(hashed_files) > 1:
                #self._text_widget.append(f"Found duplicates: {hashed_files}")
                layout = QHBoxLayout()
                widget = QWidget()
                button_group = QButtonGroup( widget )
                self._button_groups[hash] = button_group

                for idx, rel_file_path in enumerate(hashed_files):
                    file = os.path.abspath( self._base_directory + "/" +rel_file_path )
                    print(file)
                    rad_button = QRadioButton(f"Keep {rel_file_path}")
                    rad_button.setChecked( idx + 1 == len(hashed_files) )
                    rad_button.setObjectName( rel_file_path )
                    button_group.addButton( rad_button )

                    file_layout = QVBoxLayout()
                    _, file_ext = os.path.splitext( file )
                    #print(f'file: {file}')
                    pixmap = None
                    try:
                        if file_ext.lower() in [".gif", ".jpeg", ".jpg", ".png", ".bmp"]:
                            pixmap = QPixmap( file )
                    except:
                        pass
                    if pixmap is None:
                        pixmap = QPixmap( os.path.abspath( os.path.dirname(__file__) + "/../icons/linux/128.png" ) )
                    #pixmap = pixmap.scaledToWidth( 128 )
                    #label = QLabel()
                    #label.setPixmap( pixmap )
                    label = PixmapLabel()
                    label.setPixmap( pixmap )
                    #label.setStyleSheet("width: 100%; height: auto;")
                    #label.setScaledContents(True)
                    file_layout.addWidget( label )
                    file_layout.addWidget( rad_button )
                    file_layout.addStretch()

                    file_widget = QWidget()
                    file_widget.setLayout( file_layout )

                    layout.addWidget( file_widget )#
                    layout.setContentsMargins(0,0,0,0)
                    layout.addStretch()

                widget.setLayout( layout )
                scroll_area = QScrollArea()
                scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll_area.setWidgetResizable(True)
                scroll_area.setWidget(widget)
                scroll_area.setContentsMargins(0,0,0,0)
                scroll_area.setFrameStyle( Qt.FramelessWindowHint )
                duplicates_selection_widget_layout.addWidget( scroll_area )
        
        backup_dir_path_label = QLabel("Backup Directory:")

        self._backup_dir_path = QLineEdit()
        self._backup_dir_path.setReadOnly(True)

        select_backup_dir_path = QPushButton("Select")
        select_backup_dir_path.clicked.connect(self.select_backup_dir_path)

        self._remove_duplicates_button = QPushButton("Remove duplicates")
        self._remove_duplicates_button.setDisabled( True )
        self._remove_duplicates_button.clicked.connect(self.remove_duplicates)
        
        backup_dir_path = self.settings_value("backup_dir_path")
        if backup_dir_path and os.path.isdir( backup_dir_path ):
            self._backup_dir_path.setText( backup_dir_path )
            self._remove_duplicates_button.setDisabled( False )

        duplicates_selection_widget_layout.addWidget( backup_dir_path_label )
        duplicates_selection_widget_layout.addWidget( self._backup_dir_path )
        duplicates_selection_widget_layout.addWidget( select_backup_dir_path )
        duplicates_selection_widget_layout.addWidget( self._remove_duplicates_button )

        #duplicates_selection_widget_layout.addStretch()
        duplicates_selection_widget_layout.setContentsMargins(0,0,0,0)
        duplicates_selection_widget = QWidget()
        duplicates_selection_widget.setLayout( duplicates_selection_widget_layout )
        duplicates_selection_widget_scroll_area = QScrollArea()
        duplicates_selection_widget_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        duplicates_selection_widget_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        duplicates_selection_widget_scroll_area.setWidgetResizable( True )
        duplicates_selection_widget_scroll_area.setWidget( duplicates_selection_widget )
        duplicates_selection_widget_scroll_area.setContentsMargins(0,0,0,0)
        duplicates_selection_widget_scroll_area.setFrameStyle( Qt.FramelessWindowHint )
        self._layout.addWidget( duplicates_selection_widget_scroll_area )
        parent:QWidget = self.parent()
        
        QtCore.QTimer.singleShot(20, lambda: self.parent().adjustSize() if parent.width() < self._layout.sizeHint().width() or parent.height() < self._layout.sizeHint().height() else None )

    def select_backup_dir_path(self):
        dir = str (QFileDialog.getExistingDirectory(self, "Select Directory", directory=self._backup_dir_path.text() ) )
        if dir:
            dir = os.path.abspath( dir )
            self.set_settings_value("backup_dir_path", dir)
            self._backup_dir_path.setText( dir )
            self._remove_duplicates_button.setEnabled( True )
        else:
            self._backup_dir_path.setText( "" )
            self._remove_duplicates_button.setEnabled( False )
    
    def remove_duplicates(self):
        backup_dir = self._backup_dir_path.text()
        for hash, button_group in self._button_groups.items():
            rel_file_path_to_keep = button_group.checkedButton().objectName()
            for rel_path in self._hashes[hash]:
                if rel_path == rel_file_path_to_keep:
                    print(f'Would keep {rel_path}')
                    continue
                else:
                    abs_path = os.path.abspath( self._base_directory + "/" + rel_path )
                    target_path = os.path.abspath( backup_dir + "/" + rel_path )
                    parent_backup_sub_dir = os.path.dirname( target_path )
                    os.makedirs( parent_backup_sub_dir, exist_ok=True )
                    print(f'Would move {abs_path} to {target_path}')
                    shutil.move( abs_path, target_path )
        self._clear_layout()
        
        # self._layout.addWidget( self._text_widget )
        self._layout.addWidget(QLabel("Please process a directory first"))
        parent = self.parent()
        QtCore.QTimer.singleShot(20, lambda: self.parent().adjustSize() if parent.width() < self._layout.sizeHint().width() or parent.height() < self._layout.sizeHint().height() else None )

class FileOrFolderFilter(FilterWidget):
    def __init__(self, parent=None):
        FilterWidget.__init__(self, parent)

        self._base_directory = None

        self._choice = QComboBox()
        self._choice.addItem("Files and Folders")
        self._choice.addItem("Only Files")
        self._choice.addItem("Only Folders")
        self._choice.setStyleSheet("min-width: 240px;")
        self._choice.currentTextChanged.connect( lambda changed_text: self.set_settings_value("choice", changed_text) )

        layout = QVBoxLayout()
        layout.addWidget( QLabel("Enter allowed file items") )
        layout.addWidget( self._choice )
        layout.addStretch()

        self.setLayout(layout)

        # restore state
        self._choice.setCurrentText( self.settings_value( "choice", "Files and Folders" ) )

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
        self._extensions_input.textChanged.connect( lambda changed_text: self.set_settings_value("extensions", changed_text) )

        layout = QVBoxLayout()
        layout.addWidget( QLabel("Enter allowed extensions (e.g. \"*.jpg; *.txt\")") )
        layout.addWidget( self._extensions_input )
        layout.addStretch()

        self.setLayout(layout)

        # restore state
        self._extensions_input.setText( self.settings_value( "extensions", "" ) )
        
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
        #subwindow = self._mdi.addSubWindow(FesDirChooser( self ) )
        subwindow.setWindowTitle("Choose Directory")
        subwindow.show()

        # filter and processor menus
        self._filters_menu = self.menuBar().addMenu('Filters')
        self._filters_separator = self._filters_menu.addSeparator()
        self._uncheck_all_action = self._filters_menu.addAction( "Uncheck all" )
        self._uncheck_all_action.triggered.connect( self._deactivate_all_filters )
        self._processors_menu = self.menuBar().addMenu('Processors')

        # window menu
        windows_menu = self.menuBar().addMenu('Arrange Windows')
        cascade_action = windows_menu.addAction("Cascade")
        cascade_action.triggered.connect( lambda checked: self._mdi.cascadeSubWindows() )
        tile_action = windows_menu.addAction("Tile")
        tile_action.triggered.connect( lambda checked: self._mdi.tileSubWindows() )

        # add default filters and processors
        self.add_filter_widget( FileExtensionFilter() )
        self.add_filter_widget( FileOrFolderFilter() )

        self.add_processor_widget( FilePrinter() )
        self.add_processor_widget( FileStatisticsPrinter() )
        self.add_processor_widget( DeDuplicator() )

        # finalize
        self.setCentralWidget(self._mdi)    
        self.setWindowTitle("File Essentials")  
        self.setWindowIcon( QIcon( os.path.abspath( os.path.dirname(__file__) + "/../icons/Icon.ico" ) ) )

        # restore
        maximized = FesWidget.global_settings().value("maximized", False)
        if maximized:
            self.setWindowState( Qt.WindowMaximized )

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        #print("Close Event!")
        return super().closeEvent(a0)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            FesWidget.global_settings().setValue("maximized", self.windowState() == Qt.WindowMaximized)
            #if self.windowState() & Qt.WindowMaximized:
                #pass

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
        
        # restore state
        #active_filters:list[str] = json.loads( FesWidget.global_settings().value("active_filters", "[]") )
        active_filters:list[str] = FesWidget.global_settings().value("active_filters", [])
        is_active = filter_widget.name() in active_filters
        subwindow.show() if is_active else subwindow.hide()

        # add action
        action = self._filters_menu.addAction( filter_widget.name() )
        action.setObjectName( filter_widget.name() )
        action.triggered.connect( self._filter_action_clicked )
        action.setCheckable(True)
        action.setToolTip( filter_widget.description() )
        #action.setChecked(is_active)
        self._reorder_filter_menu()

    def add_processor_widget( self, processor_widget:ProcessorWidget ) -> None:
        if self.processor_widget(processor_widget.name() ) != None:
            sys.stderr.write(f"Processor widget \"{processor_widget.name()}\" already added!\n")
            return

        # add subwindow
        subwindow = self._mdi.addSubWindow(processor_widget, QtCore.Qt.WindowMinMaxButtonsHint)
        subwindow.setWindowTitle(processor_widget.name())
        active_processor_name = FesWidget.global_settings().value("active_processor")    
        is_active = processor_widget.name() == active_processor_name
        subwindow.show() if is_active else subwindow.hide()

        # add action
        action = self._processors_menu.addAction( processor_widget.name() )
        action.setObjectName( processor_widget.name() )
        action.triggered.connect( self._processor_action_clicked )
        action.setCheckable(True)
        action.setChecked(is_active)
        action.setToolTip( processor_widget.description() )
        self._reorder_filter_menu()

    def _reorder_filter_menu(self):
        active_filters:list[str] = FesWidget.global_settings().value("active_filters", [])
        actions = self._filters_menu.actions()
        #self._filters_menu.clear()
        for idx, filter_name in enumerate(active_filters):
            for action in actions:
                if action.objectName() == filter_name:
                    self._filters_menu.removeAction( action )
                    self._filters_menu.insertAction( self._filters_separator, action )
                    actions.remove( action )
                    action.setText( f'{idx+1}: {action.objectName()}' )
                    action.setChecked(True)
                    break

        for action in actions:
            if action.text() != "Uncheck all" and action.isSeparator() == False:
                action.setChecked(False)
                self._filters_menu.removeAction( action )
                #self._filters_menu.addAction( action )
                self._filters_menu.insertAction( self._filters_separator, action )
                action.setText( f'{action.objectName()}' )

    def _deactivate_all_filters(self, checked:bool=False):
        active_filters:list[str] = FesWidget.global_settings().value("active_filters", [])
        for filter_name in active_filters:
            self.filter_widget( filter_name ).parent().hide()
        FesWidget.global_settings().setValue("active_filters", [])
        self._reorder_filter_menu()


    def before_processing( self, base_directory:str ) -> None:
        for subwindow in self._mdi.subWindowList():
            widget = subwindow.widget()
            if isinstance(widget, FilterOrProcessorWidget):
                widget.before_processing(base_directory)

    def post_processing( self ) -> None:
        for subwindow in self._mdi.subWindowList():
            widget = subwindow.widget()
            if isinstance(widget, FilterOrProcessorWidget):
                widget.post_processing()

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

        #active_filters:list[str] = json.loads( FesWidget.global_settings().value("active_filters", "[]") )
        active_filters:list[str] = FesWidget.global_settings().value("active_filters", [])
        active_filters.append( filter_widget_name ) if checked else active_filters.remove( filter_widget_name )
        FesWidget.global_settings().setValue("active_filters", active_filters)
        self._reorder_filter_menu()

    def _processor_action_clicked( self, checked:bool ):   
        # get sender and processor
        action = self.sender()
        processor_name = action.objectName()
        self.toggle_processor( processor_name, checked )
    
    def toggle_processor( self, processor_name, toggle:bool ):
        # hide all except current
        for subwindow in self._mdi.subWindowList():
            widget = subwindow.widget()
            if isinstance(widget, ProcessorWidget):                
                subwindow.show() if widget.name() == processor_name else subwindow.hide()

        # uncheck all actions
        for curr_action in self._processors_menu.actions():
            curr_action.setChecked(curr_action.text() == processor_name)

        FesWidget.global_settings().setValue("active_processor", processor_name)    

    def use_file( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
        #active_filters:list[str] = FesWidget.global_settings().value("active_filters", [])

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
    #FesWidget.global_settings().clear()
    app = QApplication(sys.argv)
    fes_main_window = FesMainWindow()
    fes_main_window.show()
    app.exec_()
