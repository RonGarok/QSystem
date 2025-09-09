from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog, QTextEdit,
    QVBoxLayout, QWidget, QLineEdit, QLabel, QMessageBox
)
import pyzipper
import os
import sys

class ZipManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZipManager - QSystem")
        self.setGeometry(300, 200, 600, 500)

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("🔐 Mot de passe (optionnel)")
        self.password_input.setEchoMode(QLineEdit.Password)

        zip_btn = QPushButton("📦 Créer ZIP")
        zip_btn.clicked.connect(self.creer_zip)

        unzip_btn = QPushButton("📂 Extraire ZIP")
        unzip_btn.clicked.connect(self.extraire_zip)

        view_btn = QPushButton("👀 Voir contenu ZIP")
        view_btn.clicked.connect(self.voir_zip)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Mot de passe (optionnel pour ZIP protégé) :"))
        layout.addWidget(self.password_input)
        layout.addWidget(zip_btn)
        layout.addWidget(unzip_btn)
        layout.addWidget(view_btn)
        layout.addWidget(QLabel("🧾 Journal :"))
        layout.addWidget(self.output)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def log(self, message):
        self.output.append(message)

    def creer_zip(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Sélectionner fichiers à zipper")
        if not files:
            return

        zip_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer ZIP", "", "ZIP (*.zip)")
        if not zip_path:
            return

        password = self.password_input.text().encode() if self.password_input.text() else None

        try:
            with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
                if password:
                    zf.setpassword(password)
                for f in files:
                    zf.write(f, os.path.basename(f))
                    self.log(f"✅ Ajouté : {f}")
            self.log(f"\n📦 ZIP créé : {zip_path}")
        except Exception as e:
            self.log(f"❌ Erreur : {e}")

    def extraire_zip(self):
        zip_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner ZIP", "", "ZIP (*.zip)")
        if not zip_path:
            return

        dest_dir = QFileDialog.getExistingDirectory(self, "Choisir dossier de destination")
        if not dest_dir:
            return

        password = self.password_input.text().encode() if self.password_input.text() else None

        try:
            with pyzipper.AESZipFile(zip_path) as zf:
                if password:
                    zf.setpassword(password)
                zf.extractall(dest_dir)
                self.log(f"\n📂 ZIP extrait vers : {dest_dir}")
        except Exception as e:
            self.log(f"❌ Erreur : {e}")

    def voir_zip(self):
        zip_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner ZIP", "", "ZIP (*.zip)")
        if not zip_path:
            return

        password = self.password_input.text().encode() if self.password_input.text() else None

        try:
            with pyzipper.AESZipFile(zip_path) as zf:
                if password:
                    zf.setpassword(password)
                self.log(f"\n📁 Contenu de {zip_path} :")
                for name in zf.namelist():
                    self.log(f"  - {name}")
        except Exception as e:
            self.log(f"❌ Erreur : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ZipManager()
    window.show()
    sys.exit(app.exec_())