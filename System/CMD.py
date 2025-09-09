from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QTextEdit
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import os
import subprocess
import sys

class QSystemCMD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QSystem CMD")
        self.setGeometry(300, 200, 800, 500)
        self.cwd = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)

        layout = QVBoxLayout()
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier", 12))
        self.output.setStyleSheet("background-color: black; color: lime;")

        self.input = QLineEdit()
        self.input.setFont(QFont("Courier", 12))
        self.input.setStyleSheet("background-color: #222; color: white;")
        self.input.returnPressed.connect(self.executer_commande)

        layout.addWidget(self.output)
        layout.addWidget(self.input)
        self.setLayout(layout)

        self.log(f"QSystem CMD lancé dans : {self.cwd}")

    def log(self, message):
        self.output.append(f"> {message}")

    def executer_commande(self):
        cmd = self.input.text().strip()
        self.input.clear()

        if not cmd:
            return

        self.log(cmd)
        args = cmd.split()

        if args[0].lower() == "dir":
            try:
                fichiers = os.listdir(self.cwd)
                for f in fichiers:
                    self.output.append(f"  {f}")
            except Exception as e:
                self.log(f"Erreur : {e}")

        elif args[0].lower() == "ping":
            if len(args) < 2:
                self.log("Usage : PING <adresse>")
            else:
                try:
                    result = subprocess.check_output(["ping", args[1]], shell=True).decode()
                    self.output.append(result)
                except Exception as e:
                    self.log(f"Erreur : {e}")

        elif args[0].lower() == "start":
            if len(args) < 2:
                self.log("Usage : START <fichier.py>")
            else:
                try:
                    path = os.path.join(self.cwd, args[1])
                    subprocess.Popen(["python", path])
                    self.log(f"Lancement de {args[1]}")
                except Exception as e:
                    self.log(f"Erreur : {e}")

        elif args[0].lower() == "cd":
            if len(args) < 2:
                self.log("Usage : CD <dossier>")
            else:
                new_path = os.path.join(self.cwd, args[1])
                if os.path.isdir(new_path):
                    self.cwd = new_path
                    self.log(f"Dossier courant : {self.cwd}")
                else:
                    self.log("Dossier introuvable.")

        elif args[0].lower() == "del":
            if len(args) < 2:
                self.log("Usage : DEL <fichier>")
            else:
                path = os.path.join(self.cwd, args[1])
                if os.path.isfile(path):
                    os.remove(path)
                    self.log(f"Fichier supprimé : {args[1]}")
                else:
                    self.log("Fichier introuvable.")

        elif args[0].lower() == "mkdir":
            if len(args) < 2:
                self.log("Usage : MKDIR <nom_dossier>")
            else:
                path = os.path.join(self.cwd, args[1])
                try:
                    os.mkdir(path)
                    self.log(f"Dossier créé : {args[1]}")
                except Exception as e:
                    self.log(f"Erreur : {e}")

        elif args[0].lower() == "shutdown":
            self.log("🛑 Fermeture du CMD et de System32...")
            os.system("taskkill /f /im python.exe")
            os.system("taskkill /f /im QSystem.exe")
            sys.exit()

        else:
            self.log("Commande inconnue.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QSystemCMD()
    window.show()
    sys.exit(app.exec_())