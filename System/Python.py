from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTextEdit, QVBoxLayout,
    QWidget, QPushButton, QLabel, QHBoxLayout
)
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter
from PyQt5.QtCore import Qt, QRegExp
import subprocess
import sys
import os

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("blue"))
        keyword_format.setFontWeight(QFont.Bold)

        keywords = [
            "def", "class", "import", "from", "as", "if", "elif", "else",
            "try", "except", "finally", "for", "while", "return", "with",
            "lambda", "pass", "break", "continue", "global", "nonlocal", "assert"
        ]

        self.rules = [(QRegExp(r"\b" + kw + r"\b"), keyword_format) for kw in keywords]

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("darkGreen"))
        self.rules.append((QRegExp(r'"[^"]*"'), string_format))
        self.rules.append((QRegExp(r"'[^']*'"), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("gray"))
        self.rules.append((QRegExp(r"#.*"), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)

class PythonEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Editor - QSystem")
        self.setGeometry(300, 200, 800, 600)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Courier", 12))
        PythonHighlighter(self.editor.document())

        self.output = QLabel()
        self.output.setStyleSheet("color: white; background-color: #222; padding: 5px;")
        self.output.setAlignment(Qt.AlignTop)
        self.output.setWordWrap(True)

        open_btn = QPushButton("📂 Ouvrir .py")
        open_btn.clicked.connect(self.ouvrir_fichier)

        run_btn = QPushButton("▶️ Exécuter")
        run_btn.clicked.connect(self.executer_script)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(open_btn)
        btn_layout.addWidget(run_btn)

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self.editor)
        layout.addWidget(QLabel("🧪 Sortie :"))
        layout.addWidget(self.output)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def ouvrir_fichier(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir fichier Python", "", "Python (*.py)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.setText(f.read())
            self.current_path = path

    def executer_script(self):
        code = self.editor.toPlainText()
        temp_path = os.path.join(os.path.dirname(__file__), "temp_exec.py")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            result = subprocess.check_output(["python", temp_path], stderr=subprocess.STDOUT, timeout=5)
            self.output.setText(result.decode())
        except subprocess.CalledProcessError as e:
            self.output.setText(f"Erreur :\n{e.output.decode()}")
        except Exception as e:
            self.output.setText(f"Exception : {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PythonEditor()
    window.show()
    sys.exit(app.exec_())