from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidget, QVBoxLayout, QWidget, QLabel
import os
import sys

class FileExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fichier - QSystem")
        self.setGeometry(350, 200, 600, 400)

        self.root_path = os.path.dirname(os.path.abspath(sys.argv[0]))

        self.list_widget = QListWidget()
        self.label = QLabel(f"📁 Racine : {self.root_path}")
        self.label.setStyleSheet("font-weight: bold;")

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.list_widget)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.afficher_contenu()

    def afficher_contenu(self):
        self.list_widget.clear()
        for item in os.listdir(self.root_path):
            self.list_widget.addItem(item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileExplorer()
    window.show()
    sys.exit(app.exec_())