import math
import os
import platform
import shutil
import subprocess
import tempfile
import traceback
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, \
    QListWidget, QFileDialog, QAbstractItemView, QMessageBox, QProgressDialog, QApplication, QLabel, QTextEdit, \
    QSplitter, QGroupBox

from PyQt5.QtWidgets import QMainWindow
from fbs_runtime.application_context.PyQt5 import ApplicationContext
import sys
import fe_interfaces
import fe_model


class DragDropListWidget(QListWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAcceptDrops(True)

    # The following three methods set up dragging and dropping for the app
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        """
        Drop files directly onto the widget
        File locations are stored in fname
        :param e:
        :return:
        """
        if e.mimeData().hasUrls:
            e.setDropAction(QtCore.Qt.CopyAction)
            e.accept()
            # Workaround for OSx dragging and dropping
            for url in e.mimeData().urls():
                file_name = str(url.toLocalFile())
                if os.path.isfile(file_name):
                    self.addItem(file_name)
        else:
            e.ignore()


class CentralWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        # build gui

        # left_widget
        left_widget = FilePathsWidget(self)

        # right_widget
        filters_widget = FilesFunctionWidget("Filters")
        filters_widget.add_files_function(fe_model.NoneFilter())
        filters_widget.add_files_function(fe_model.NoneFilter())
        processors_widget = FilesFunctionWidget("Processors")
        processors_widget.add_files_function(fe_model.NoneProcessor())
        processors_widget.add_files_function(fe_model.NoneProcessor())
        console_widget = QTextEdit("")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0);
        right_layout.addWidget(filters_widget)
        right_layout.addWidget(processors_widget)
        right_layout.addWidget(console_widget)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        # self layout
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)


class FilesFunctionWidget(QWidget):
    def __init__(self, headline, parent=None):
        QWidget.__init__(self, parent)

        # left_widget
        self.filesFunctions = []  # List[fe_interfaces.FilesFunction]

        # build gui
        self.box = QGroupBox(headline)
        self.build_box_layout()

        # self layout
        layout = QVBoxLayout()
        layout.addWidget(self.box)
        self.setLayout(layout)

    def add_files_function(self, filesFunction: fe_interfaces.FilesFunction):
        self.filesFunctions.append(filesFunction)
        self.build_box_layout()

    def build_box_layout(self):
        if self.box.layout():
            QWidget().setLayout(self.box.layout())
        layout = QVBoxLayout()
        if len(self.filesFunctions) == 0:
            label = QLabel("None")
            inner_layout = QHBoxLayout()
            inner_layout.addWidget(label)
            layout.addLayout(inner_layout)
        else:
            for filesFunction in self.filesFunctions:
                label = QLabel(filesFunction.to_String())
                remove_button = QPushButton("\u2796")
                remove_button.setStyleSheet("font-size: 18px; font-weight: bold")
                edit_button = QPushButton("\u270E")
                edit_button.setStyleSheet("font-size: 18px; font-weight: bold")
                inner_layout = QHBoxLayout()
                inner_layout.addWidget(label)
                inner_layout.addWidget(remove_button)
                inner_layout.addWidget(edit_button)
                inner_layout.addStretch(1)
                layout.addLayout(inner_layout)

        add_button = QPushButton("\u2795")
        add_button.setStyleSheet("font-size: 18px; font-weight: bold")
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        self.box.setLayout(layout)

class FilePathsWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        # build gui
        # the dir chooser
        add_files_button = QPushButton('Add files')
        add_files_button.clicked.connect(self.add_files_button_clicked)
        change_dir_button = QPushButton('Scan Directory')
        change_dir_button.clicked.connect(self.change_dir_button_clicked)
        dir_chooser_layout = QHBoxLayout()
        dir_chooser_layout.addWidget(add_files_button)
        dir_chooser_layout.addWidget(change_dir_button)

        # the file_list
        self.file_list = DragDropListWidget()
        # self.file_list.setEnabled(False)
        self.file_list.itemSelectionChanged.connect(self.file_list_item_selection_changed)
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.model().rowsInserted.connect(self.file_list_model_rows_inserted)
        self.file_list.model().rowsRemoved.connect(self.file_list_model_rows_removed)
        self.file_list.model().modelReset.connect(self.file_list_model_model_reset)

        # the file_list_action_bar
        self.remove_file_button = QPushButton('Remove File')
        self.remove_file_button.clicked.connect(self.remove_file_button_clicked)
        self.remove_file_button.setEnabled(False)
        self.move_up_button = QPushButton('Move Up')
        self.move_up_button.clicked.connect(self.move_up_button_clicked)
        self.move_up_button.setEnabled(False)
        self.move_down_button = QPushButton('Move Down')
        self.move_down_button.clicked.connect(self.move_down_button_clicked)
        self.move_down_button.setEnabled(False)
        self.remove_all_button = QPushButton('Remove All')
        self.remove_all_button.clicked.connect(self.remove_all_button_clicked)
        self.remove_all_button.setEnabled(False)
        file_list_action_bar_layout = QHBoxLayout()
        file_list_action_bar_layout.setContentsMargins(0, 0, 0, 0);
        file_list_action_bar_layout.addWidget(self.remove_file_button)
        file_list_action_bar_layout.addWidget(self.move_up_button)
        file_list_action_bar_layout.addWidget(self.move_down_button)
        file_list_action_bar_layout.addWidget(self.remove_all_button)
        self.file_list_action_bar_widget = QWidget()
        self.file_list_action_bar_widget.setLayout(file_list_action_bar_layout)

        central_widget_layout = QVBoxLayout()
        central_widget_layout.addLayout(dir_chooser_layout)
        central_widget_layout.addWidget(self.file_list)
        central_widget_layout.addWidget(self.file_list_action_bar_widget)

        box_layout = QVBoxLayout()
        box_layout.addLayout(central_widget_layout)
        box = QGroupBox("Files")
        box.setLayout(box_layout)

        layout = QVBoxLayout()
        layout.addWidget(box)
        self.setLayout(layout)
        self.setAcceptDrops(True)

        # conversion state
        self.tmp_dir = None
        self.current_file_idx = -1
        self.tmp_files = []

    def file_list_model_rows_removed(self):
        self.remove_all_button.setEnabled(self.file_list.count() > 0)
        self.output_file_widget.setEnabled(self.file_list.count() > 0)

    def file_list_model_rows_inserted(self):
        self.remove_all_button.setEnabled(self.file_list.count() > 0)
        self.output_file_widget.setEnabled(True)

    def file_list_model_model_reset(self):
        self.remove_all_button.setEnabled(False)
        self.output_file_widget.setEnabled(False)

    def convert_next_file(self):
        if self.progress_dialog.wasCanceled():
            self.current_file_idx = len(self.files_to_be_converted)
            return
        self.progress_dialog.setValue(self.current_file_idx)
        QApplication.processEvents()

        if self.current_file_idx < len(self.files_to_be_converted):

            file_path = self.files_to_be_converted[self.current_file_idx]
            self.current_file_idx = self.current_file_idx + 1

            file_name = str(self.current_file_idx).zfill(12)
            _, file_ext = os.path.splitext(file_path)
            tmp_file_path = os.path.join(self.tmp_dir, file_name + file_ext)

            self.tmp_files.append(tmp_file_path)
            if file_ext in [".jpeg", ".jpg", ".bmp"]:
                with open(tmp_file_path, "wb") as f:
                    pass
                self.convert_next_file()
            elif file_ext in [".pdf"]:
                shutil.copy2(file_path, tmp_file_path)
                self.convert_next_file()
            elif file_ext in [".html"]:
                loader = QtWebEngineWidgets.QWebEngineView()
                loader.setZoomFactor(1)
                loader.load(QtCore.QUrl.fromLocalFile(file_path))

                def pdf_convert_finished():
                    self.convert_next_file()

                def emit_pdf(finished):
                    loader.page().printToPdf(tmp_file_path)

                loader.page().pdfPrintingFinished.connect(pdf_convert_finished)
                loader.loadFinished.connect(emit_pdf)
        else:
            # do the merge
            merger = None

            for file in self.tmp_files:
                merger.append(file)
            output_file_path = self.output_file_line_edit.text()
            merger.write(output_file_path)
            merger.close()

            # clean up
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

            # close progress dialog
            self.progress_dialog.close()
            self.progress_dialog = None

            # show the success
            reply = QMessageBox.information(self, "PdfMerge", "PDF Creation successful!",
                                            QMessageBox.Ok | QMessageBox.Open)
            if reply == QMessageBox.Open:
                self.open_file(output_file_path)

    def merge_button_clicked(self):
        self.files_to_be_converted = []
        self.tmp_dir = tempfile.mkdtemp()
        self.current_file_idx = 0
        self.tmp_files = []

        for index in range(0, self.file_list.count()):
            self.files_to_be_converted.append(self.file_list.item(index).text())

        try:
            self.progress_dialog = QProgressDialog("Processing ...", "Cancel", 0, len(self.files_to_be_converted), self)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setAutoClose(False)
            self.progress_dialog.setAutoReset(False)
            self.progress_dialog.show()

            self.convert_next_file()
        except:
            err = traceback.print_exc()
            QMessageBox.critical(self, "An error occured", "PDF could not be generated. Error: {}".format(err))

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
                if self.progress_dialog.wasCanceled():
                    return []
                self.progress_dialog.setValue(i)
                QApplication.processEvents()

                i = i + 1 if i < 100 else 0
                fname, fext = os.path.splitext(file)
                if fext.lower() in self.get_supported_files():
                    files.append(os.path.join(root, file))

        self.progress_dialog.close()
        self.progress_dialog = None
        return files

    def file_list_item_selection_changed(self):
        list_items = self.file_list.selectedItems()
        if not list_items:
            self.move_down_button.setEnabled(False)
            self.move_up_button.setEnabled(False)
            self.remove_file_button.setEnabled(False)
        else:
            self.remove_file_button.setEnabled(True)
            self.move_down_button.setEnabled(len(list_items) == 1)
            self.move_up_button.setEnabled(len(list_items) == 1)

    def add_files_button_clicked(self):
        # self.file_list.clear()
        file_types = "Supported Types ("
        for supp_file_type in self.get_supported_files():
            file_types = file_types + "*" + supp_file_type + " "
        file_types = file_types + ")"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "()", file_types)
        for file in files:
            self.file_list.addItem(file)

    def change_dir_button_clicked(self):
        # self.file_list.clear()
        # self.file_list.setEnabled(False)
        self.output_file_widget.setEnabled(False)
        dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if dir:
            files = self.scan_files(dir)
            for file in files:
                self.file_list.addItem(file)
            if len(files) > 0:
                # self.file_list.setEnabled(True)
                self.output_file_widget.setEnabled(True)

    def remove_file_button_clicked(self):
        list_items = self.file_list.selectedItems()
        if not list_items:
            return
        for item in list_items:
            self.file_list.takeItem(self.file_list.row(item))

    def remove_all_button_clicked(self):
        self.file_list.clear()

    def move_up_button_clicked(self):
        list_items = self.file_list.selectedItems()
        if not list_items:
            return
        currentRow = self.file_list.currentRow()
        if currentRow == 0:
            self.file_list.setCurrentRow(currentRow)
            self.file_list.setFocus()
            return
        currentItem = self.file_list.takeItem(currentRow)
        self.file_list.insertItem(currentRow - 1, currentItem)
        # currentItem.setSelected(True)
        self.file_list.setCurrentRow(currentRow - 1)
        self.file_list.setFocus()

    def move_down_button_clicked(self):
        list_items = self.file_list.selectedItems()
        if not list_items:
            return
        currentRow = self.file_list.currentRow()
        if currentRow + 1 == self.file_list.count():
            self.file_list.setCurrentRow(currentRow)
            self.file_list.setFocus()
            return
        currentItem = self.file_list.takeItem(currentRow)
        self.file_list.insertItem(currentRow + 1, currentItem)
        self.file_list.setCurrentRow(currentRow + 1)
        # currentItem.setSelected(True)
        self.file_list.setFocus()

    def output_file_change_button_clicked(self):
        fileName = QFileDialog.getSaveFileName(self,
                                               self.tr("Export document to PDF"),
                                               "", self.tr("PDF files (*.pdf)"))[0]
        if fileName:
            self.output_file_line_edit.setText(fileName)
            self.merge_button.setEnabled(True)
        else:
            self.merge_button.setEnabled(False)

    def open_file(self, filepath):
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', filepath))
        elif platform.system() == 'Windows':  # Windows
            os.startfile(filepath)
        else:  # linux variants
            subprocess.call(('xdg-open', filepath))


def start():
    # 1. Instantiate ApplicationContext
    app_context = ApplicationContext()

    # qmainwindow
    version = app_context.build_settings['version']
    app_name = app_context.build_settings['app_name']
    window_title = app_name + " v" + version
    window = QMainWindow()
    window.setWindowTitle(window_title)
    window.setCentralWidget(CentralWidget())
    window.resize(800, 600)
    window.showMaximized()
    # window.show()

    # run
    # app_context.app.setStyleSheet(qdarkstyle.load_stylesheet())
    exit_code = app_context.app.exec_()  # 2. Invoke app_context.app.exec_()
    sys.exit(exit_code)
