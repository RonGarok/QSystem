import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

# Style Mendel (sombre)
APP_STYLE = """
QMainWindow { background-color: #0b0b0b; color: #fff; }
QWidget { background-color: #0b0b0b; color: #fff; }
QPushButton, QLineEdit {
    background-color: #2f2f2f;
    color: #fff;
    border: 1px solid #444;
    padding: 6px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #3a3a3a; }
QPushButton:pressed { background-color: #1f1f1f; }
QLabel { color: #ddd; }
"""

class MendelBrowser(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Navigateur Mendel")
        self.setMinimumSize(960, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Barre d'URL
        bar = QHBoxLayout()
        bar.setSpacing(6)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://vornak.city")
        self.url_input.returnPressed.connect(self.load_url)
        bar.addWidget(self.url_input, 1)

        self.go_btn = QPushButton("Aller")
        self.go_btn.clicked.connect(self.load_url)
        bar.addWidget(self.go_btn)

        layout.addLayout(bar)

        # Vue Web
        self.web = QWebEngineView()
        self.web.setUrl(QUrl("https://www.mozilla.org"))
        layout.addWidget(self.web, 1)

        # Status
        self.status = QLabel("Prêt")
        layout.addWidget(self.status)

    def load_url(self):
        url = self.url_input.text().strip()
        if not url:
            self.status.setText("URL vide")
            return
        if not url.startswith("http"):
            url = "https://" + url
        self.web.setUrl(QUrl(url))
        self.status.setText(f"Chargement : {url}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    w = MendelBrowser()
    w.show()
    sys.exit(app.exec_())
