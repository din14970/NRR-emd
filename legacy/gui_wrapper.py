#!./.venv/bin python3

from PyQt5.QtWidgets import (QApplication, QWidget, QCheckBox, QComboBox,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout)

import sys


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.title = "Non-rigid registration utility"
        self.setWindowTitle(self.title)
        self.layout = QVBoxLayout()
        self.create_widgets()
        self.setLayout(self.layout)
        self.show()

    def create_widgets(self):
        #button to pull up the EMD conversion
        self.emdbutton = QPushButton("Convert EMD to images/spectra")
        self.emdbutton.clicked.connect(self.convert_emd)
        self.layout.addWidget(self.emdbutton)

        #button for generating the config file
        self.configbutton = QPushButton("Generate config file")
        self.configbutton.clicked.connect(self.create_config_file)
        self.layout.addWidget(self.configbutton)

        self.calcbutton = QPushButton("Calculate deformations")
        self.calcbutton.clicked.connect(self.execute_nonrigid)
        self.layout.addWidget(self.calcbutton)

        self.applybutton = QPushButton("Apply deformations to images/spectra")
        self.applybutton.clicked.connect(self.apply_nonrigid)
        self.layout.addWidget(self.applybutton)


    def convert_emd(self):
        pass

    def create_config_file(self):
        pass

    def execute_nonrigid(self):
        pass

    def apply_nonrigid(self):
        pass


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
