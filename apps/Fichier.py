# apps/FileExplorer.py
import sys
import os
import shutil
from contextlib import suppress
from PyQt5.QtWidgets import (
    QApplication, QWidget, QListWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QLineEdit, QFileDialog, QMessageBox, QInputDialog, QMenu
)
from PyQt5.QtCore import Qt, QDir, QSize
from PyQt5.QtGui import QFont, QCursor

# Styles Mendel
BG = "background-color: black;"
PANEL_STYLE = "background-color: #2f2f2f; border-radius: 8px;"
LIST_STYLE = """
QListWidget {
    background: transparent;
    color: #ffffff;
    border: none;
    padding: 6px;
}
QListWidget::item {
    padding: 6px 8px;
}
QListWidget::item:selected {
    background: rgba(255,255,255,0.06);
}
"""

BUTTON_STYLE = """
QPushButton {
    background-color: #505050;
    color: white;
    border: 1px solid #616161;
    padding: 6px 10px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #5c5c5c; }
QPushButton:pressed { background-color: #474747; }
"""

DANGER_STYLE = """
QPushButton {
    background-color: #8B2E2E;
    color: white;
    border: 1px solid #6a1f1f;
    padding: 6px 10px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #9e3a3a; }
"""

class FileExplorer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fichier")
        self.setStyleSheet(BG)
        self.setFixedSize(720, 520)

        # Project root = parent of apps (assumes this file sits in projectroot/apps/)
        this_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(this_dir, ".."))
        self.root_path = project_root

        # Current path starts at root
        self.current_path = self.root_path

        # Clipboard for copy/cut operations
        self.clipboard = []  # list of absolute paths
        self.clipboard_mode = None  # 'copy' or 'cut'

        # UI
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(10)

        # Header: path display and controls
        header = QHBoxLayout()
        header.setSpacing(8)

        self.path_label = QLabel()
        self.path_label.setStyleSheet("color: white; font-weight: bold;")
        self.path_label.setFont(QFont("Arial", 11))
        header.addWidget(self.path_label, 1)

        btn_up = QPushButton("↑")
        btn_up.setToolTip("Remonter d'un niveau")
        btn_up.setFixedSize(QSize(36, 28))
        btn_up.setStyleSheet(BUTTON_STYLE)
        btn_up.clicked.connect(self.go_up)
        header.addWidget(btn_up)

        btn_refresh = QPushButton("⟳")
        btn_refresh.setToolTip("Rafraîchir")
        btn_refresh.setFixedSize(QSize(36, 28))
        btn_refresh.setStyleSheet(BUTTON_STYLE)
        btn_refresh.clicked.connect(self.refresh)
        header.addWidget(btn_refresh)

        main.addLayout(header)

        # Panel area
        panel_layout = QHBoxLayout()
        panel_layout.setSpacing(10)

        # Left: file list
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(LIST_STYLE)
        self.list_widget.itemDoubleClicked.connect(self.on_double_click)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_context_menu)
        left_layout.addWidget(self.list_widget, 1)

        panel_layout.addLayout(left_layout, 3)

        # Right: actions
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        lbl_actions = QLabel("Actions")
        lbl_actions.setStyleSheet("color: white; font-weight: bold;")
        right_layout.addWidget(lbl_actions)

        btn_new_file = QPushButton("Nouveau fichier")
        btn_new_file.setStyleSheet(BUTTON_STYLE)
        btn_new_file.clicked.connect(self.new_file)
        right_layout.addWidget(btn_new_file)

        btn_new_folder = QPushButton("Nouveau dossier")
        btn_new_folder.setStyleSheet(BUTTON_STYLE)
        btn_new_folder.clicked.connect(self.new_folder)
        right_layout.addWidget(btn_new_folder)

        btn_rename = QPushButton("Renommer")
        btn_rename.setStyleSheet(BUTTON_STYLE)
        btn_rename.clicked.connect(self.rename_item)
        right_layout.addWidget(btn_rename)

        btn_delete = QPushButton("Supprimer")
        btn_delete.setStyleSheet(DANGER_STYLE)
        btn_delete.clicked.connect(self.delete_item)
        right_layout.addWidget(btn_delete)

        btn_copy = QPushButton("Copier")
        btn_copy.setStyleSheet(BUTTON_STYLE)
        btn_copy.clicked.connect(self.copy_item)
        right_layout.addWidget(btn_copy)

        btn_cut = QPushButton("Couper")
        btn_cut.setStyleSheet(BUTTON_STYLE)
        btn_cut.clicked.connect(self.cut_item)
        right_layout.addWidget(btn_cut)

        btn_paste = QPushButton("Coller")
        btn_paste.setStyleSheet(BUTTON_STYLE)
        btn_paste.clicked.connect(self.paste_item)
        right_layout.addWidget(btn_paste)

        btn_open = QPushButton("Ouvrir fichier...")
        btn_open.setStyleSheet(BUTTON_STYLE)
        btn_open.clicked.connect(self.open_file_dialog)
        right_layout.addWidget(btn_open)

        right_layout.addStretch()
        panel_layout.addLayout(right_layout, 1)

        main.addLayout(panel_layout)

        # Bottom: status
        self.status = QLabel()
        self.status.setStyleSheet("color: #ccc;")
        main.addWidget(self.status)

    # ----------------- Navigation / refresh -----------------
    def refresh(self):
        try:
            self.path_label.setText(f"📁 {self.current_path}")
            self.list_widget.clear()
            entries = sorted(os.listdir(self.current_path), key=lambda x: x.lower())
            for name in entries:
                self.list_widget.addItem(name)
            self.status.setText(f"{len(entries)} éléments")
        except Exception as e:
            self._show_error(f"Impossible d'ouvrir le répertoire : {e}")

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if os.path.exists(parent) and os.path.commonpath([parent, self.root_path]) == self.root_path:
            self.current_path = parent
            self.refresh()
        elif parent == '' or os.path.abspath(parent) == os.path.abspath(self.current_path):
            # already root
            self._show_info("Déjà à la racine du projet")
        else:
            # parent outside root: don't allow
            self._show_info("Impossible de remonter au‑delà du root du projet")

    def on_double_click(self, item):
        name = item.text()
        full = os.path.join(self.current_path, name)
        if os.path.isdir(full):
            # only allow browsing inside project root
            common = os.path.commonpath([os.path.abspath(full), self.root_path])
            if common != self.root_path:
                self._show_info("Accès au dossier refusé (en dehors du projet)")
                return
            self.current_path = full
            self.refresh()
        else:
            # open file with default app
            with suppress(Exception):
                if sys.platform == "win32":
                    os.startfile(full)
                elif sys.platform == "darwin":
                    subprocess_run(["open", full])
                else:
                    subprocess_run(["xdg-open", full])

    # ----------------- Context menu -----------------
    def on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        menu = QMenu()
        if item:
            name = item.text()
            menu.addAction("Ouvrir", lambda: self._open_selected(item))
            menu.addAction("Renommer", lambda: self.rename_item(item))
            menu.addAction("Copier", lambda: self.copy_item(item))
            menu.addAction("Couper", lambda: self.cut_item(item))
            menu.addAction("Coller ici", lambda: self.paste_item())
            menu.addAction("Supprimer", lambda: self.delete_item(item))
            menu.addSeparator()
            menu.addAction("Propriétés", lambda: self.show_properties(item))
        else:
            menu.addAction("Coller ici", lambda: self.paste_item())
            menu.addAction("Nouveau dossier", self.new_folder)
            menu.addAction("Nouveau fichier", self.new_file)
        menu.exec_(QCursor.pos())

    def _open_selected(self, item):
        self.on_double_click(item)

    # ----------------- Basic operations -----------------
    def _selected_path(self, item=None):
        if item is None:
            item = self.list_widget.currentItem()
        if not item:
            return None
        return os.path.join(self.current_path, item.text())

    def new_folder(self):
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
        if not ok or not name.strip():
            return
        dest = os.path.join(self.current_path, name.strip())
        try:
            os.makedirs(dest, exist_ok=False)
            self.refresh()
        except FileExistsError:
            self._show_error("Le dossier existe déjà.")
        except Exception as e:
            self._show_error(f"Impossible de créer le dossier : {e}")

    def new_file(self):
        name, ok = QInputDialog.getText(self, "Nouveau fichier", "Nom du fichier :")
        if not ok or not name.strip():
            return
        dest = os.path.join(self.current_path, name.strip())
        if os.path.exists(dest):
            self._show_error("Le fichier existe déjà.")
            return
        try:
            with open(dest, "w", encoding="utf-8") as f:
                f.write("")  # create empty file
            self.refresh()
        except Exception as e:
            self._show_error(f"Impossible de créer le fichier : {e}")

    def rename_item(self, item=None):
        path = self._selected_path(item)
        if not path:
            self._show_info("Sélectionnez un élément à renommer.")
            return
        new_name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=os.path.basename(path))
        if not ok or not new_name.strip():
            return
        dest = os.path.join(self.current_path, new_name.strip())
        try:
            os.rename(path, dest)
            self.refresh()
        except Exception as e:
            self._show_error(f"Impossible de renommer : {e}")

    def delete_item(self, item=None):
        path = self._selected_path(item)
        if not path:
            self._show_info("Sélectionnez un élément à supprimer.")
            return
        # Confirm
        if os.path.isdir(path):
            msg = f"Supprimer le dossier et tout son contenu ?\n{path}"
        else:
            msg = f"Supprimer le fichier ?\n{path}"
        if not self._confirm(msg):
            return
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.refresh()
        except Exception as e:
            self._show_error(f"Impossible de supprimer : {e}")

    # ----------------- copy / cut / paste -----------------
    def copy_item(self, item=None):
        path = self._selected_path(item)
        if not path:
            self._show_info("Sélectionnez un élément à copier.")
            return
        self.clipboard = [path]
        self.clipboard_mode = "copy"
        self._show_info("Copié dans le presse-papier")

    def cut_item(self, item=None):
        path = self._selected_path(item)
        if not path:
            self._show_info("Sélectionnez un élément à couper.")
            return
        self.clipboard = [path]
        self.clipboard_mode = "cut"
        self._show_info("Coupé dans le presse-papier")

    def paste_item(self):
        if not self.clipboard:
            self._show_info("Presse-papier vide")
            return
        for src in self.clipboard:
            name = os.path.basename(src)
            dst = os.path.join(self.current_path, name)
            # avoid overwrite: ask
            if os.path.exists(dst):
                if not self._confirm(f"Remplacer {dst} ?"):
                    continue
                # attempt to remove existing
                try:
                    if os.path.isdir(dst) and not os.path.islink(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                except Exception as e:
                    self._show_error(f"Impossible d'écraser {dst} : {e}")
                    continue
            try:
                if self.clipboard_mode == "copy":
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                elif self.clipboard_mode == "cut":
                    shutil.move(src, dst)
                else:
                    # unknown mode fallback to copy
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            except Exception as e:
                self._show_error(f"Erreur lors du collage : {e}")
        # after paste, if cut then clear clipboard
        if self.clipboard_mode == "cut":
            self.clipboard = []
            self.clipboard_mode = None
        self.refresh()

    # ----------------- file open dialog -----------------
    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir fichier", self.current_path)
        if path:
            # open file with default app
            with suppress(Exception):
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess_run(["open", path])
                else:
                    subprocess_run(["xdg-open", path])

    def show_properties(self, item):
        path = self._selected_path(item)
        if not path:
            return
        try:
            size = os.path.getsize(path) if os.path.isfile(path) else "-"
            info = f"Chemin : {path}\nType : {'Dossier' if os.path.isdir(path) else 'Fichier'}\nTaille : {size}"
            self._show_info(info)
        except Exception as e:
            self._show_error(f"Impossible d'obtenir les propriétés : {e}")

    # ----------------- helpers -----------------
    def _confirm(self, message):
        mb = QMessageBox(self)
        mb.setWindowTitle("Confirmation")
        mb.setText(message)
        mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        mb.setDefaultButton(QMessageBox.No)
        mb.setStyleSheet("QMessageBox { background-color: #2f2f2f; color: #fff; }")
        return mb.exec_() == QMessageBox.Yes

    def _show_error(self, message):
        mb = QMessageBox(self)
        mb.setIcon(QMessageBox.Critical)
        mb.setWindowTitle("Erreur")
        mb.setText(message)
        mb.setStyleSheet("QMessageBox { background-color: #2f2f2f; color: #fff; }")
        mb.exec_()

    def _show_info(self, message):
        mb = QMessageBox(self)
        mb.setWindowTitle("Info")
        mb.setText(message)
        mb.setStyleSheet("QMessageBox { background-color: #2f2f2f; color: #fff; }")
        mb.exec_()

# small helper for subprocess.run cross-platform usage without import error
def subprocess_run(cmd):
    with suppress(Exception):
        import subprocess
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FileExplorer()
    w.show()
    sys.exit(app.exec_())
