# apps/Paint.py
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QColorDialog, QMessageBox,
    QLabel, QToolBar, QAction, QSpinBox, QComboBox, QSlider, QStatusBar,
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox, QInputDialog
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor, QIcon, QImage, QMouseEvent, QKeySequence, QFont
)
from PyQt5.QtCore import Qt, QPoint, QRect

# Styles Mendel (sombre)
APP_STYLE = """
QMainWindow { background-color: #0b0b0b; color: #fff; }
QToolBar { background: #222; spacing: 6px; }
QPushButton, QComboBox, QSpinBox, QSlider {
    background: #2f2f2f; color: #fff; border: 1px solid #444; padding: 4px;
}
QLabel { color: #ddd; }
QStatusBar { background: #101010; color: #ddd; }
"""

TOOLS = [
    "Crayon", "Pinceau", "Gomme", "Remplir", "Pipette",
    "Ligne", "Rectangle", "Ellipse", "Texte", "Sélection"
]

class Canvas(QLabel):
    def __init__(self, width=1200, height=800, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)

        self._zoom = 1.0
        self._canvas_size = (width, height)
        self.pixmap_orig = QPixmap(width, height)
        self.pixmap_orig.fill(Qt.white)
        self.setPixmap(self.pixmap_orig.copy())

        # drawing state
        self.drawing = False
        self.last_point = QPoint()
        self.start_point = QPoint()
        self.current_tool = "Crayon"
        self.pen_color = QColor("black")
        self.bg_color = QColor("white")
        self.pen_width = 3
        self.pen_opacity = 255
        self.fill_mode = False  # for rectangle/ellipse
        self.eraser_size = 20
        self.selection_rect = None
        self.selection_pixmap = None
        self.selection_offset = QPoint()
        self.is_selecting = False
        self.lock = False

        # Undo/Redo stacks (store QImage)
        self.undo_stack = []
        self.redo_stack = []
        self._push_undo()  # initial state

        # grid
        self.show_grid = False
        self.grid_spacing = 25

    # ---- state helpers ----
    def _push_undo(self):
        # store a copy of current image
        self.undo_stack.append(self.pixmap().toImage().copy())
        if len(self.undo_stack) > 40:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) < 2:
            return
        cur = self.undo_stack.pop()  # current
        self.redo_stack.append(cur)
        img = self.undo_stack[-1]
        self.setPixmap(QPixmap.fromImage(img))
        self.update()

    def redo(self):
        if not self.redo_stack:
            return
        img = self.redo_stack.pop()
        self.undo_stack.append(img)
        self.setPixmap(QPixmap.fromImage(img))
        self.update()

    def clear(self, color=Qt.white):
        self._push_undo()
        self.pixmap_orig.fill(color)
        self.setPixmap(self.pixmap_orig.copy()) 
        self.update()

    def open_image(self, path):
        img = QImage(path)
        if img.isNull():
            raise RuntimeError("Impossible d'ouvrir l'image")
        w, h = img.width(), img.height()
        self._canvas_size = (w, h)
        self.pixmap_orig = QPixmap.fromImage(img.convertToFormat(QImage.Format_ARGB32))
        self.setPixmap(self.pixmap_orig.copy())
        self._push_undo()

    def save_image(self, path, format=None):
        self.pixmap().save(path, format or None)

    # ---- mouse events ----
    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() != Qt.LeftButton or self.lock:
            return
        pos = ev.pos() / self._zoom
        pos = QPoint(int(pos.x()), int(pos.y()))
        self.drawing = True
        self.start_point = pos
        self.last_point = pos

        if self.current_tool == "Pipette":
            color = QColor(self.pixmap().toImage().pixel(pos))
            self.pen_color = color
            self.parent().color_changed(color)
            return

        if self.current_tool == "Remplir":
            self._push_undo()
            self.flood_fill(pos, self.pen_color)
            return

        if self.current_tool == "Sélection":
            self.is_selecting = True
            self.selection_rect = QRect(pos, pos)
            return

    def mouseMoveEvent(self, ev: QMouseEvent):
        pos = ev.pos() / self._zoom
        pos = QPoint(int(pos.x()), int(pos.y()))
        if not self.drawing and not self.is_selecting:
            return

        if self.current_tool in ("Crayon", "Pinceau", "Gomme"):
            painter = QPainter(self.pixmap())
            if self.current_tool == "Gomme":
                pen = QPen(self.bg_color, self.eraser_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            else:
                pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                pen.setColor(self.pen_color)
            pen.setCosmetic(False)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawLine(self.last_point, pos)
            painter.end()
            self.last_point = pos
            self.update()
            return

        # shape drawing: update temporary overlay on a copy
        if self.current_tool in ("Ligne", "Rectangle", "Ellipse", "Texte"):
            # draw on a temp copy for preview
            tmp = self.pixmap_orig.copy()
            p = QPainter(tmp)
            pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.setRenderHint(QPainter.Antialiasing)
            if self.current_tool == "Ligne":
                p.drawLine(self.start_point, pos)
            elif self.current_tool == "Rectangle":
                rect = QRect(self.start_point, pos)
                if self.fill_mode:
                    p.fillRect(rect, self.pen_color)
                else:
                    p.drawRect(rect)
            elif self.current_tool == "Ellipse":
                rect = QRect(self.start_point, pos)
                if self.fill_mode:
                    p.setBrush(self.pen_color)
                    p.drawEllipse(rect)
                else:
                    p.drawEllipse(rect)
            p.end()
            self.setPixmap(tmp)
            return

        if self.current_tool == "Sélection" and self.is_selecting:
            self.selection_rect.setBottomRight(pos)
            tmp = self.pixmap_orig.copy()
            p = QPainter(tmp)
            pen = QPen(QColor(200,200,200), 1, Qt.DashLine)
            p.setPen(pen)
            p.drawRect(self.selection_rect)
            p.end()
            self.setPixmap(tmp)
            return

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if ev.button() != Qt.LeftButton or self.lock:
            return
        pos = ev.pos() / self._zoom
        pos = QPoint(int(pos.x()), int(pos.y()))
        self.drawing = False

        if self.current_tool in ("Crayon", "Pinceau", "Gomme"):
            self._push_undo()
            self.pixmap_orig = self.pixmap().copy()
            return

        if self.current_tool in ("Ligne", "Rectangle", "Ellipse"):
            self._push_undo()
            p = QPainter(self.pixmap())
            pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.setRenderHint(QPainter.Antialiasing)
            if self.current_tool == "Ligne":
                p.drawLine(self.start_point, pos)
            elif self.current_tool == "Rectangle":
                rect = QRect(self.start_point, pos)
                if self.fill_mode:
                    p.fillRect(rect, self.pen_color)
                else:
                    p.drawRect(rect)
            elif self.current_tool == "Ellipse":
                rect = QRect(self.start_point, pos)
                if self.fill_mode:
                    p.setBrush(self.pen_color)
                    p.drawEllipse(rect)
                else:
                    p.drawEllipse(rect)
            p.end()
            # commit to original
            self.pixmap_orig = self.pixmap().copy()
            return

        if self.current_tool == "Sélection" and self.is_selecting:
            self.is_selecting = False
            if self.selection_rect and not self.selection_rect.isNull():
                sr = self.selection_rect.normalized()
                self.selection_pixmap = self.pixmap().copy(sr)
                self._push_undo()
                # erase area in original
                p = QPainter(self.pixmap())
                p.fillRect(sr, self.bg_color)
                p.end()
                self.pixmap_orig = self.pixmap().copy()
            return

    # ---- drawing helpers ----
    def flood_fill(self, start_pt: QPoint, color: QColor):
        img = self.pixmap().toImage()
        w, h = img.width(), img.height()
        target = QColor(img.pixel(start_pt)).rgba()
        replacement = color.rgba()
        if target == replacement:
            return
        stack = [start_pt]
        while stack:
            p = stack.pop()
            x, y = p.x(), p.y()
            if x < 0 or x >= w or y < 0 or y >= h:
                continue
            if QColor(img.pixel(x,y)).rgba() != target:
                continue
            img.setPixel(x, y, color.rgba())
            stack.extend([QPoint(x+1,y), QPoint(x-1,y), QPoint(x,y+1), QPoint(x,y-1)])
        self.setPixmap(QPixmap.fromImage(img))
        self.pixmap_orig = self.pixmap().copy()

    # ---- transforms ----
    def rotate90(self, cw=True):
        self._push_undo()
        img = self.pixmap().toImage()
        transform = img.transformed(Qt.QTransform().rotate(90 if cw else -90))
        self.pixmap_orig = QPixmap.fromImage(transform)
        self.setPixmap(self.pixmap_orig.copy())

    def flip(self, horizontal=True):
        self._push_undo()
        img = self.pixmap().toImage()
        mirrored = img.mirrored(horizontal, not horizontal)
        self.pixmap_orig = QPixmap.fromImage(mirrored)
        self.setPixmap(self.pixmap_orig.copy())

    def invert_colors(self):
        self._push_undo()
        img = self.pixmap().toImage()
        img.invertPixels()
        self.pixmap_orig = QPixmap.fromImage(img)
        self.setPixmap(self.pixmap_orig.copy())

    def zoom(self, factor):
        self._zoom = factor
        scaled = self.pixmap_orig.scaled(self.pixmap_orig.width()*factor, self.pixmap_orig.height()*factor, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)
        self.update()

    def crop(self, rect: QRect):
        if rect.isNull():
            return
        self._push_undo()
        img = self.pixmap().toImage().copy(rect)
        self.pixmap_orig = QPixmap.fromImage(img)
        self.setPixmap(self.pixmap_orig.copy())

class PaintMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paint - Mendel")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(APP_STYLE)

        # Canvas
        self.canvas = Canvas(1200, 700, self)
        self.setCentralWidget(self.canvas)

        # Toolbar
        self._create_toolbar()
        self._create_menubar()
        self._create_statusbar()

    def _create_toolbar(self):
        tb = QToolBar("Outils")
        tb.setIconSize(Qt.QSize(20,20))
        self.addToolBar(Qt.LeftToolBarArea, tb)

        # Tool actions
        self.tool_actions = {}
        for t in TOOLS:
            a = QAction(t, self)
            a.setCheckable(True)
            a.triggered.connect(lambda checked, name=t: self.select_tool(name))
            tb.addAction(a)
            self.tool_actions[t] = a
        self.select_tool("Crayon")

        tb.addSeparator()
        color_btn = QPushButton("Couleur")
        color_btn.clicked.connect(self.choose_color)
        tb.addWidget(color_btn)

        tb.addSeparator()
        tb.addWidget(QLabel("Épaisseur"))
        spin = QSpinBox()
        spin.setRange(1, 200)
        spin.setValue(3)
        spin.valueChanged.connect(self.set_pen_width)
        tb.addWidget(spin)

        tb.addWidget(QLabel("Opacité"))
        s = QSlider(Qt.Horizontal)
        s.setRange(10, 255)
        s.setValue(255)
        s.valueChanged.connect(self.set_opacity)
        tb.addWidget(s)

        tb.addSeparator()
        undo_btn = QAction("Annuler", self)
        undo_btn.triggered.connect(self.canvas.undo)
        tb.addAction(undo_btn)
        redo_btn = QAction("Rétablir", self)
        redo_btn.triggered.connect(self.canvas.redo)
        tb.addAction(redo_btn)

        tb.addSeparator()
        save_btn = QAction("Enregistrer", self)
        save_btn.triggered.connect(self.save_file)
        tb.addAction(save_btn)

        open_btn = QAction("Ouvrir", self)
        open_btn.triggered.connect(self.open_file)
        tb.addAction(open_btn)

        new_btn = QAction("Nouveau", self)
        new_btn.triggered.connect(self.new_file)
        tb.addAction(new_btn)

        # shapes fill toggle
        self.fill_toggle = QCheckBox("Remplir")
        self.fill_toggle.stateChanged.connect(lambda s: setattr(self.canvas, "fill_mode", bool(s)))
        tb.addWidget(self.fill_toggle)

        # grid toggle
        self.grid_toggle = QCheckBox("Grille")
        self.grid_toggle.stateChanged.connect(lambda s: setattr(self.canvas, "show_grid", bool(s)))
        tb.addWidget(self.grid_toggle)

        # rotate / flip
        tb.addSeparator()
        rot_l = QAction("Rotation -90°", self); rot_l.triggered.connect(lambda: self.canvas.rotate90(cw=False))
        rot_r = QAction("Rotation +90°", self); rot_r.triggered.connect(lambda: self.canvas.rotate90(cw=True))
        tb.addAction(rot_l); tb.addAction(rot_r)
        flip_h = QAction("Miroir H", self); flip_h.triggered.connect(lambda: self.canvas.flip(horizontal=True))
        flip_v = QAction("Miroir V", self); flip_v.triggered.connect(lambda: self.canvas.flip(horizontal=False))
        tb.addAction(flip_h); tb.addAction(flip_v)

        # invert colors
        inv = QAction("Inverser couleurs", self); inv.triggered.connect(self.canvas.invert_colors)
        tb.addAction(inv)

        # zoom combobox
        tb.addSeparator()
        self.zoom_box = QComboBox()
        self.zoom_box.addItems(["50%", "75%", "100%", "150%", "200%", "300%", "400%"])
        self.zoom_box.setCurrentText("100%")
        self.zoom_box.currentTextChanged.connect(lambda t: self.on_zoom(t))
        tb.addWidget(self.zoom_box)

    def _create_menubar(self):
        mb = self.menuBar()
        filem = mb.addMenu("Fichier")
        new = QAction("Nouveau", self); new.triggered.connect(self.new_file); filem.addAction(new)
        opena = QAction("Ouvrir...", self); opena.triggered.connect(self.open_file); filem.addAction(opena)
        save = QAction("Enregistrer", self); save.triggered.connect(self.save_file); filem.addAction(save)
        saveas = QAction("Enregistrer sous...", self); saveas.triggered.connect(self.save_file_as); filem.addAction(saveas)
        exp = QAction("Exporter PNG...", self); exp.triggered.connect(self.export_png); filem.addAction(exp)
        filem.addSeparator()
        exita = QAction("Quitter", self); exita.triggered.connect(self.close); filem.addAction(exita)

        edit = mb.addMenu("Édition")
        undo = QAction("Annuler", self); undo.setShortcut("Ctrl+Z"); undo.triggered.connect(self.canvas.undo); edit.addAction(undo)
        redo = QAction("Rétablir", self); redo.setShortcut("Ctrl+Y"); redo.triggered.connect(self.canvas.redo); edit.addAction(redo)
        clear = QAction("Effacer tout", self); clear.triggered.connect(lambda: self.canvas.clear(self.canvas.bg_color)); edit.addAction(clear)

        view = mb.addMenu("Affichage")
        grid = QAction("Afficher grille", self); grid.setCheckable(True); grid.triggered.connect(lambda s: setattr(self.canvas, "show_grid", bool(s))); view.addAction(grid)

        tools = mb.addMenu("Outils")
        pip = QAction("Pipette", self); pip.triggered.connect(lambda: self.select_tool("Pipette")); tools.addAction(pip)
        fill = QAction("Remplir", self); fill.triggered.connect(lambda: self.select_tool("Remplir")); tools.addAction(fill)
        sel = QAction("Sélection", self); sel.triggered.connect(lambda: self.select_tool("Sélection")); tools.addAction(sel)

    def _create_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.coord_label = QLabel("x:0 y:0")
        sb.addPermanentWidget(self.coord_label)
        self.color_label = QLabel()
        self.color_label.setFixedSize(24,24)
        self.color_label.setStyleSheet("background: black; border:1px solid #444")
        sb.addPermanentWidget(self.color_label)

    # ---- UI slots ----
    def select_tool(self, name):
        # uncheck others
        for t, a in self.tool_actions.items():
            a.setChecked(t == name)
        self.canvas.current_tool = name
        self.statusBar().showMessage(f"Outil: {name}")

    def choose_color(self):
        col = QColorDialog.getColor(self.canvas.pen_color, self, "Choisir couleur")
        if col.isValid():
            self.canvas.pen_color = col
            self.color_changed(col)

    def color_changed(self, col: QColor):
        self.color_label.setStyleSheet(f"background: {col.name()}; border: 1px solid #444")

    def set_pen_width(self, w):
        self.canvas.pen_width = w

    def set_opacity(self, v):
        self.canvas.pen_opacity = v

    def on_zoom(self, text):
        try:
            val = int(text.replace("%", "")) / 100.0
            self.canvas.zoom(val)
        except Exception:
            pass

    # ---- file operations ----
    def new_file(self):
        res = QMessageBox.question(self, "Nouveau", "Créer une nouvelle image ? (perd les modifications non enregistrées)", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self.canvas.clear(Qt.white)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir image", "", "Images (*.png *.jpg *.bmp *.gif);;Tous les fichiers (*)")
        if path:
            try:
                self.canvas.open_image(path)
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def save_file(self):
        # simple save to last path — for now ask "save as"
        self.save_file_as()

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", "", "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)")
        if path:
            fmt = None
            if path.lower().endswith(".png"):
                fmt = "PNG"
            elif path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
                fmt = "JPG"
            elif path.lower().endswith(".bmp"):
                fmt = "BMP"
            try:
                self.canvas.save_image(path, fmt)
                QMessageBox.information(self, "Enregistré", f"Sauvegardé : {path}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PNG", "", "PNG (*.png)")
        if path:
            try:
                self.canvas.save_image(path, "PNG")
                QMessageBox.information(self, "Exporté", f"Exporté : {path}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    # ---- keyboard ----
    def keyPressEvent(self, ev):
        if ev.matches(QKeySequence.Undo):
            self.canvas.undo()
        elif ev.matches(QKeySequence.Redo):
            self.canvas.redo()
        elif ev.matches(QKeySequence.Save):
            self.save_file()
        elif ev.matches(QKeySequence.Open):
            self.open_file()
        elif ev.key() == Qt.Key_Delete:
            if self.canvas.selection_rect:
                self.canvas._push_undo()
                p = QPainter(self.canvas.pixmap())
                p.fillRect(self.canvas.selection_rect, self.canvas.bg_color)
                p.end()
                self.canvas.pixmap_orig = self.canvas.pixmap().copy()

def main():
    app = QApplication(sys.argv)
    w = PaintMain()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
