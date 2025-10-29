# apps/Calculator.py
import sys
import math
import traceback
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton, QLineEdit, QFrame,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Styles Mendel
PANEL_STYLE = "QFrame { background-color: #2f2f2f; border-radius: 12px; }"
DISPLAY_STYLE = """
QLineEdit {
    background-color: #111111;
    color: #ffffff;
    border: 1px solid #333333;
    padding: 10px;
    border-radius: 6px;
    font-size: 24px;
}
"""
BUTTON_STYLE = """
QPushButton {
    background-color: #505050;
    color: #ffffff;
    border: 1px solid #616161;
    border-radius: 8px;
    font-size: 16px;
    min-width: 56px;
    min-height: 44px;
}
QPushButton:hover { background-color: #5c5c5c; }
QPushButton:pressed { background-color: #3f3f3f; }
"""

SCIENTIFIC_BUTTON_STYLE = """
QPushButton {
    background-color: #454545;
    color: #ffffff;
    border: 1px solid #5a5a5a;
    border-radius: 6px;
    font-size: 14px;
    min-width: 56px;
    min-height: 40px;
}
QPushButton:hover { background-color: #555555; }
QPushButton:pressed { background-color: #3b3b3b; }
"""

# Safe math names for evaluation
SAFE_NAMES = {k: getattr(math, k) for k in (
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "log", "log10", "exp", "sqrt", "degrees", "radians",
    "floor", "ceil", "fabs"
)}
SAFE_NAMES.update({"pi": math.pi, "e": math.e})

def safe_eval_expr(expr, local_safe=None):
    expr = expr.replace("^", "**")
    import re
    expr = re.sub(r'(\d+(\.\d+)?)\%', r'(\1/100)', expr)
    local = (local_safe.copy() if local_safe else SAFE_NAMES.copy())
    try:
        return eval(expr, {"__builtins__": None}, local)
    except Exception:
        raise

class Calculator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculatrice")
        self.setStyleSheet("background-color: black;")
        # default standard size and scientific size
        self.standard_size = (360, 520)
        self.sci_size = (420, 760)
        self.setFixedSize(*self.standard_size)

        # Panel (with extra padding)
        container = QFrame(self)
        container.setStyleSheet(PANEL_STYLE)
        container.setFixedSize(340, 520)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)

        # Display
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setStyleSheet(DISPLAY_STYLE)
        self.display.setFont(QFont("Arial", 20))
        container_layout.addWidget(self.display)

        # Memory register
        self.memory = 0.0

        # Top controls: scientific toggle and spacer
        top_h = QHBoxLayout()
        top_h.setSpacing(8)
        self.sci_toggle = QPushButton("Mode scientifique")
        self.sci_toggle.setCheckable(True)
        self.sci_toggle.setStyleSheet(BUTTON_STYLE)
        self.sci_toggle.clicked.connect(self.toggle_scientific)
        top_h.addWidget(self.sci_toggle)

        top_h.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        container_layout.addLayout(top_h)

        # Scientific area (in its own widget with margin)
        self.sci_widget = QFrame()
        self.sci_widget.setStyleSheet("QFrame { background: transparent; }")
        sci_wrap = QVBoxLayout(self.sci_widget)
        sci_wrap.setContentsMargins(0, 8, 0, 8)  # extra vertical padding to separate sections
        sci_wrap.setSpacing(8)

        # scientific grid
        sci_grid = QGridLayout()
        sci_grid.setSpacing(8)
        sci_buttons = [
            ('sin', 0, 0), ('cos', 0, 1), ('tan', 0, 2), ('^', 0, 3),
            ('asin', 1, 0), ('acos', 1, 1), ('atan', 1, 2), ('sqrt', 1, 3),
            ('ln', 2, 0), ('log', 2, 1), ('e', 2, 2), ('pi', 2, 3),
            ('exp', 3, 0), ('abs', 3, 1), ('floor', 3, 2), ('ceil', 3, 3),
            ('(', 4, 0), (')', 4, 1), ('fac', 4, 2), ('deg', 4, 3),
        ]
        for text, r, c in sci_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(SCIENTIFIC_BUTTON_STYLE)
            btn.setFont(QFont("Arial", 12))
            btn.clicked.connect(lambda _, t=text: self.on_click(t))
            sci_grid.addWidget(btn, r, c)
        sci_wrap.addLayout(sci_grid)

        # Add a subtle separator line between scientific and standard area
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.06); border: none;")
        container_layout.addWidget(self.sci_widget)
        container_layout.addWidget(sep)

        # Standard keypad layout with more spacing
        pad_layout = QGridLayout()
        pad_layout.setSpacing(10)
        pad_layout.setContentsMargins(0, 8, 0, 0)

        std_buttons = [
            ('MC', 0, 0), ('MR', 0, 1), ('M+', 0, 2), ('M-', 0, 3),
            ('C', 1, 0), ('←', 1, 1), ('%', 1, 2), ('/', 1, 3),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2), ('*', 2, 3),
            ('4', 3, 0), ('5', 3, 1), ('6', 3, 2), ('-', 3, 3),
            ('1', 4, 0), ('2', 4, 1), ('3', 4, 2), ('+', 4, 3),
            ('±', 5, 0), ('0', 5, 1), ('.', 5, 2), ('=', 5, 3),
        ]
        for text, r, c in std_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(BUTTON_STYLE)
            btn.setFont(QFont("Arial", 14))
            btn.clicked.connect(lambda _, t=text: self.on_click(t))
            pad_layout.addWidget(btn, r, c)

        container_layout.addLayout(pad_layout)

        # Center the container in the main window
        main_layout = QVBoxLayout(self)
        main_layout.addStretch()
        main_layout.addWidget(container, 0, Qt.AlignCenter)
        main_layout.addStretch()
        self.setLayout(main_layout)

        # Internal state
        self.last_result = ""
        self.user_is_typing = False

        # Initially hide scientific area
        self.sci_widget.setVisible(False)
        sep.setVisible(False)
        self.sep = sep

    # ---------- button handling ----------
    def on_click(self, text):
        try:
            if text == 'C':
                self.display.clear()
                self.user_is_typing = False
                return
            if text == '←':
                self.display.setText(self.display.text()[:-1])
                return
            if text == '±':
                cur = self.display.text()
                if cur.startswith('-'):
                    self.display.setText(cur[1:])
                else:
                    self.display.setText('-' + cur)
                return
            if text == '=':
                self.calculate()
                return
            if text == 'MC':
                self.memory = 0.0
                return
            if text == 'MR':
                self.display.setText(str(self.memory))
                return
            if text == 'M+':
                try:
                    val = float(self.safe_current_value())
                    self.memory += val
                except Exception:
                    pass
                return
            if text == 'M-':
                try:
                    val = float(self.safe_current_value())
                    self.memory -= val
                except Exception:
                    pass
                return
            if text == '%':
                self.display.setText(self.display.text() + "%")
                return

            mapping = {
                'ln': 'log', 'log': 'log10', '^': '^', 'pi': 'pi', 'e': 'e',
                'sqrt': 'sqrt', 'exp': 'exp', 'abs': 'fabs', 'fac': 'factorial',
                'deg': 'degrees(', 'sin': 'sin(', 'cos': 'cos(', 'tan': 'tan(',
                'asin': 'asin(', 'acos': 'acos(', 'atan': 'atan(', 'floor': 'floor', 'ceil': 'ceil'
            }
            if text in mapping:
                tok = mapping[text]
                # append token; functions with '(' already include it
                self.display.setText(self.display.text() + tok)
                return
            # parentheses or digits/operators
            self.display.setText(self.display.text() + text)
        except Exception:
            self.display.setText("Erreur")

    def safe_current_value(self):
        txt = self.display.text().strip()
        if txt == '':
            return '0'
        return txt

    def calculate(self):
        expr = self.display.text().strip()
        if not expr:
            return
        local_safe = SAFE_NAMES.copy()
        local_safe.update({"factorial": math.factorial})
        try:
            expr_prepared = expr.replace('^', '**').replace('%', '/100')
            result = eval(expr_prepared, {"__builtins__": None}, local_safe)
            if isinstance(result, float):
                if abs(result) < 1e-12:
                    result = 0.0
                s = ('{:.12g}'.format(result))
            else:
                s = str(result)
            self.display.setText(s)
            self.last_result = s
        except Exception:
            # fallback to safe_eval_expr
            try:
                r = safe_eval_expr(expr, local_safe)
                s = ('{:.12g}'.format(r)) if isinstance(r, float) else str(r)
                self.display.setText(s)
                self.last_result = s
            except Exception:
                self.display.setText("Erreur")

    def toggle_scientific(self):
        enabled = self.sci_toggle.isChecked()
        self.sci_widget.setVisible(enabled)
        self.sep.setVisible(enabled)
        if enabled:
            self.setFixedSize(*self.sci_size)
        else:
            self.setFixedSize(*self.standard_size)

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        if text in '0123456789.+-*/^()':
            self.display.setText(self.display.text() + text)
            return
        if key == Qt.Key_Backspace:
            self.display.setText(self.display.text()[:-1])
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.calculate()
            return
        if key == Qt.Key_Escape:
            self.display.clear()
            return
        super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Calculator()
    win.show()
    sys.exit(app.exec_())
