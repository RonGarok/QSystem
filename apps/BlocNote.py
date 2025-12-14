#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTextEdit, QListWidget, QListWidgetItem, QFileDialog, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# --- Chemins (l'app est dans apps/, on remonte d'un dossier vers la racine) ---
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))  # remonte d'un dossier
USER_DIR = os.path.join(PROJECT_ROOT, "user")
os.makedirs(USER_DIR, exist_ok=True)

# --- Styles (cohérents avec ManagerTool/Mendel) ---
PANEL_STYLE = "QFrame { background-color: #2f2f2f; border-radius: 12px; }"
LABEL_STYLE = "color: white; font-size: 13px;"
BUTTON_STYLE = """
QPushButton {
    background-color: #505050;
    color: white;
    border: 1px solid #616161;
    padding: 6px 12px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #5c5c5c; }
QPushButton:pressed { background-color: #474747; }
"""
LIST_STYLE = """
QListWidget {
    background-color: #2b2b2b;
    color: #eaeaea;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
}
QListWidget::item:selected { background: #3a3a3a; }
"""
TEXTEDIT_STYLE = """
QTextEdit {
    background-color: #1f1f1f;
    color: #f0f0f0;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    font-size: 14px;
}
"""
LINEEDIT_STYLE = """
QLineEdit {
    background-color: #2b2b2b;
    color: #ffffff;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 4px 8px;
}
"""

def safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    cleaned = "".join(ch for ch in name.strip() if ch not in bad)
    return cleaned if cleaned else "sans_nom.txt"

class BlocNote(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bloc Note")
        self.setStyleSheet("background-color: black;")
        self.setMinimumSize(820, 560)

        # Logo
        self.logo = QLabel("M", self)
        self.logo.setFont(QFont("Arial", 60, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.logo.move(10, 10)

        # Conteneur principal
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # En-tête
        header = QFrame(self)
        header.setStyleSheet(PANEL_STYLE)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)

        title = QLabel("Bloc Note — Dossier utilisateur")
        title.setStyleSheet("color: white; font-size: 16px;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.path_label = QLabel(USER_DIR)
        self.path_label.setStyleSheet("color: #bbbbbb; font-size: 12px;")
        header_layout.addWidget(self.path_label)

        root.addWidget(header)

        # Corps
        body = QFrame(self)
        body.setStyleSheet(PANEL_STYLE)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(12)

        # Liste des fichiers (user/)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(8)

        lbl_files = QLabel("Fichiers (user/)")
        lbl_files.setStyleSheet(LABEL_STYLE)
        left_panel.addWidget(lbl_files)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet(LIST_STYLE)
        self.file_list.itemSelectionChanged.connect(self.on_file_selected)
        left_panel.addWidget(self.file_list)

        # Actions fichiers (nouveau / renommer / supprimer)
        file_actions = QHBoxLayout()
        self.new_btn = QPushButton("Nouveau")
        self.new_btn.setStyleSheet(BUTTON_STYLE)
        self.new_btn.clicked.connect(self.new_file)
        file_actions.addWidget(self.new_btn)

        self.rename_btn = QPushButton("Renommer")
        self.rename_btn.setStyleSheet(BUTTON_STYLE)
        self.rename_btn.clicked.connect(self.rename_file)
        file_actions.addWidget(self.rename_btn)

        self.delete_btn = QPushButton("Supprimer")
        self.delete_btn.setStyleSheet(BUTTON_STYLE)
        self.delete_btn.clicked.connect(self.delete_file)
        file_actions.addWidget(self.delete_btn)

        left_panel.addLayout(file_actions)

        # À gauche dans le layout principal
        body_layout.addLayout(left_panel, 1)

        # Éditeur
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        self.current_name_edit = QLineEdit()
        self.current_name_edit.setPlaceholderText("Nom du fichier (ex: notes.txt)")
        self.current_name_edit.setStyleSheet(LINEEDIT_STYLE)
        right_panel.addWidget(self.current_name_edit)

        self.editor = QTextEdit()
        self.editor.setStyleSheet(TEXTEDIT_STYLE)
        right_panel.addWidget(self.editor, 1)

        # Actions d'édition (ouvrir externe / sauvegarder / enregistrer sous)
        edit_actions = QHBoxLayout()

        self.open_external_btn = QPushButton("Ouvrir (sélectionner un fichier)")
        self.open_external_btn.setStyleSheet(BUTTON_STYLE)
        self.open_external_btn.clicked.connect(self.open_external_file)
        edit_actions.addWidget(self.open_external_btn)

        self.save_btn = QPushButton("Enregistrer")
        self.save_btn.setStyleSheet(BUTTON_STYLE)
        self.save_btn.clicked.connect(self.save_current)
        edit_actions.addWidget(self.save_btn)

        self.save_as_btn = QPushButton("Enregistrer sous… (user/)")
        self.save_as_btn.setStyleSheet(BUTTON_STYLE)
        self.save_as_btn.clicked.connect(self.save_as_user)
        edit_actions.addWidget(self.save_as_btn)

        right_panel.addLayout(edit_actions)

        body_layout.addLayout(right_panel, 2)

        root.addWidget(body)

        # Statut
        footer = QFrame(self)
        footer.setStyleSheet(PANEL_STYLE)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.setSpacing(8)
        self.status = QLabel("Prêt")
        self.status.setStyleSheet("color: #cccccc;")
        footer_layout.addWidget(self.status)
        root.addWidget(footer)

        # Mise à jour liste initiale
        QTimer.singleShot(50, self.refresh_file_list)

        # Données
        self.current_path = None  # chemin réel du fichier édité (peut être hors user/ s'il a été ouvert externe)

    # --- Utilitaires ---
    def set_status(self, text):
        self.status.setText(text)

    def refresh_file_list(self):
        self.file_list.clear()
        try:
            files = sorted([f for f in os.listdir(USER_DIR)
                            if os.path.isfile(os.path.join(USER_DIR, f)) and f.lower().endswith(".txt")])
            for f in files:
                item = QListWidgetItem(f)
                self.file_list.addItem(item)
            self.set_status(f"{len(files)} fichier(s) listés dans user/")
        except Exception as e:
            self.set_status(f"Erreur lecture user/: {e}")

    def on_file_selected(self):
        items = self.file_list.selectedItems()
        if not items:
            return
        name = items[0].text()
        path = os.path.join(USER_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.setText(content)
            self.current_name_edit.setText(name)
            self.current_path = path
            self.set_status(f"Chargé: {name}")
        except Exception as e:
            self.set_status(f"Erreur ouverture: {e}")

    # --- Actions fichiers côté user/ ---
    def new_file(self):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"notes_{ts}.txt"
        self.current_name_edit.setText(default_name)
        self.editor.clear()
        self.current_path = os.path.join(USER_DIR, default_name)
        self.set_status("Nouveau fichier (non enregistré)")

    def rename_file(self):
        if not self.current_path or not os.path.exists(self.current_path):
            QMessageBox.warning(self, "Renommer", "Aucun fichier ouvert à renommer.")
            return
        new_name = safe_filename(self.current_name_edit.text())
        if not new_name.lower().endswith(".txt"):
            new_name += ".txt"
        new_path = os.path.join(USER_DIR, new_name)
        if os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(self.current_path):
            QMessageBox.warning(self, "Renommer", "Un fichier avec ce nom existe déjà.")
            return
        try:
            os.replace(self.current_path, new_path)
            self.current_path = new_path
            self.current_name_edit.setText(new_name)
            self.set_status(f"Renommé en {new_name}")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self, "Renommer", f"Erreur: {e}")

    def delete_file(self):
        if not self.current_path or not os.path.exists(self.current_path):
            QMessageBox.warning(self, "Supprimer", "Aucun fichier ouvert à supprimer.")
            return
        reply = QMessageBox.question(self, "Supprimer", "Supprimer ce fichier ?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            os.remove(self.current_path)
            self.current_path = None
            self.editor.clear()
            self.current_name_edit.clear()
            self.set_status("Fichier supprimé")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self, "Supprimer", f"Erreur: {e}")

    # --- Ouverture externe et sauvegardes ---
    def open_external_file(self):
        # permet de charger un fichier depuis n'importe où (lecture), mais enregistre toujours vers user/
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier texte", PROJECT_ROOT, "Textes (*.txt);;Tous (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.setText(content)
            base = os.path.basename(path)
            self.current_name_edit.setText(base if base.lower().endswith(".txt") else base + ".txt")
            self.current_path = path  # chemin source (lecture)
            self.set_status(f"Ouvert (lecture): {base}")
        except Exception as e:
            QMessageBox.critical(self, "Ouvrir", f"Erreur: {e}")

    def save_current(self):
        # Enregistre dans user/, même si l'origine est externe
        name = safe_filename(self.current_name_edit.text())
        if not name.lower().endswith(".txt"):
            name += ".txt"
        dst = os.path.join(USER_DIR, name)
        try:
            with open(dst, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.current_path = dst
            self.set_status(f"Enregistré: {name}")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self, "Enregistrer", f"Erreur: {e}")

    def save_as_user(self):
        # Demande un nom mais force l'emplacement vers user/
        name, ok = QFileDialog.getSaveFileName(self, "Enregistrer sous (user/)", USER_DIR, "Textes (*.txt)")
        if not ok or not name:
            return
        # Normalise vers user/ quoi qu’il arrive
        base = os.path.basename(name)
        base = safe_filename(base)
        if not base.lower().endswith(".txt"):
            base += ".txt"
        dst = os.path.join(USER_DIR, base)
        try:
            with open(dst, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.current_path = dst
            self.current_name_edit.setText(base)
            self.set_status(f"Enregistré: {base}")
            self.refresh_file_list()
        except Exception as e:
            QMessageBox.critical(self, "Enregistrer sous", f"Erreur: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # garder le logo en haut-gauche
        self.logo.move(10, 10)


def main():
    app = QApplication(sys.argv)
    w = BlocNote()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
