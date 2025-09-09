from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QPushButton, QLineEdit
import sys

class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calculatrice - QSystem")
        self.setGeometry(400, 250, 300, 400)

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("font-size: 24px;")
        self.layout.addWidget(self.display, 0, 0, 1, 4)

        self.create_buttons()

    def create_buttons(self):
        buttons = [
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('/', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('-', 3, 3),
            ('0', 4, 0), ('.', 4, 1), ('=', 4, 2), ('+', 4, 3),
        ]

        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(60, 60)
            btn.clicked.connect(lambda _, t=text: self.on_click(t))
            self.layout.addWidget(btn, row, col)

    def on_click(self, text):
        if text == '=':
            try:
                result = str(eval(self.display.text()))
                self.display.setText(result)
            except:
                self.display.setText("Erreur")
        else:
            self.display.setText(self.display.text() + text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Calculator()
    window.show()
    sys.exit(app.exec_())
