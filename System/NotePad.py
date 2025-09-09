from PyQt5.QtWidgets import QMainWindow, QTextEdit, QAction, QFileDialog, QApplication
import sys

class NotePad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NotePad - QSystem")
        self.setGeometry(300, 200, 600, 400)

        self.text_area = QTextEdit()
        self.setCentralWidget(self.text_area)

        self.init_menu()

    def init_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("Fichier")

        open_action = QAction("Ouvrir", self)
        open_action.triggered.connect(self.ouvrir_fichier)
        file_menu.addAction(open_action)

        save_action = QAction("Enregistrer", self)
        save_action.triggered.connect(self.enregistrer_fichier)
        file_menu.addAction(save_action)

    def ouvrir_fichier(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir fichier", "", "Texte (*.txt)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.text_area.setText(f.read())

    def enregistrer_fichier(self):
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", "", "Texte (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text_area.toPlainText())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NotePad()
    window.show()
    sys.exit(app.exec_())