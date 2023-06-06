# FileEssentials
FileEssentials is a GUI tool frontend for multiple file utilities.
It supports Plugin like usage of file filters and appropriate file processors.

## Installation
Install using the installer package for Windows. Or use python to build on your own.

## Manual
Self explaining :)

# Extending FileEssentials
1. Clone the repo
2. Make sure to have a python 3.5/3.6 interpeter because of fbs free requirements (see https://build-system.fman.io/#licensing)
3. Use pip install -r requirements.txt
4. Import "main.py"
5. Create your own classes by inherting from
> main.BasicSubWindow

or
> main.FilterSubWindow

or
> main.ProcessorSubWindow
6. Example code:
> 
    import sys

    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QLabel
    from fbs_runtime.application_context.PyQt5 import ApplicationContext

    sys.path.append("E:\\git\\FileEssentials\\src\\main\\python") # TODO: ADAPT the path!!
    import main

    class CustomProcessor( main.ProcessorSubWindow ):    
        def __init__(self, parent=None, flags:Qt.WindowFlags=Qt.WindowFlags()):
            main.ProcessorSubWindow.__init__(self, parent, flags)

            layout = QVBoxLayout()
            layout.addWidget(QLabel(self.description()))

            widget = QWidget()
            widget.setLayout( layout )

            self.setWidget(widget)         
        
        def name( self ) -> str:
            return "CustomProcessor"
        
        def description( self ) -> str:
            return "Prints the file path into the console"

        def before_processing( self ) -> None:
            self.main_window().console().reset()

        def process( self, abs_file_path:str, rel_file_path:str, level:int ) -> bool:
            self.main_window().console().append( f'{rel_file_path}' )

        
    if __name__ == '__main__':
        #main.fes_settings.clear()

        appctxt = ApplicationContext()
        fes_main_window = main.FesMainWindow()
        fes_main_window.create_sub_window( CustomProcessor )
        fes_main_window.show()
        exit_code = appctxt.app.exec()
        sys.exit(exit_code)
