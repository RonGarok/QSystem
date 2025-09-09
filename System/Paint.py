from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QColorDialog,
    QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QPoint
import sys

class PaintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paint - QSystem")
        self.setGeometry(200, 150, 900, 600)

        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor("black")
        self.pen_width = 3

        self.canvas = QLabel()
        self.canvas.setPixmap(QPixmap(900, 500))
        self.canvas.pixmap().fill(Qt.white)

        self.init_ui()

    def init_ui(self):
        color_btn = QPushButton("🎨 Couleur")
        color_btn.clicked.connect(self.choose_color)

        clear_btn = QPushButton("🗑️ Effacer")
        clear_btn.clicked.connect(self.clear_canvas)

        save_btn = QPushButton("💾 Sauvegarder")
        save_btn.clicked.connect(self.save_image)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(color_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        if self.drawing:
            painter = QPainter(self.canvas.pixmap())
            pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.last_point - self.canvas.pos(), event.pos() - self.canvas.pos())
            self.last_point = event.pos()
            self.canvas.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.pen_color = color

    def clear_canvas(self):
        self.canvas.pixmap().fill(Qt.white)
        self.canvas.update()

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder image", "", "PNG (*.png)")
        if path:
            self.canvas.pixmap().save(path, "PNG")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PaintApp()
    window.show()
    sys.exit(app.exec_())