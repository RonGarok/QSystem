from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QPushButton, QLabel
)
from PyQt5.QtCore import QTimer
import psutil
import sys
import os

class TaskManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Manager - QSystem")
        self.setGeometry(300, 200, 700, 500)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["PID", "Nom", "CPU %", "RAM %"])
        self.table.setColumnWidth(1, 250)

        self.refresh_btn = QPushButton("🔄 Rafraîchir")
        self.refresh_btn.clicked.connect(self.refresh)

        self.kill_btn = QPushButton("🛑 Terminer le processus sélectionné")
        self.kill_btn.clicked.connect(self.kill_selected)

        self.status = QLabel("🧠 Chargement des processus...")

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.kill_btn)
        layout.addWidget(self.status)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.refresh()
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)

    def refresh(self):
        self.table.setRowCount(0)
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if "python" in proc.info['name'].lower():
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(str(proc.info['pid'])))
                    self.table.setItem(row, 1, QTableWidgetItem(proc.info['name']))
                    self.table.setItem(row, 2, QTableWidgetItem(f"{proc.info['cpu_percent']}"))
                    self.table.setItem(row, 3, QTableWidgetItem(f"{round(proc.info['memory_percent'], 2)}"))
            except Exception:
                continue
        self.status.setText("✅ Liste mise à jour.")

    def kill_selected(self):
        selected = self.table.currentRow()
        if selected >= 0:
            pid_item = self.table.item(selected, 0)
            if pid_item:
                pid = int(pid_item.text())
                try:
                    psutil.Process(pid).terminate()
                    self.status.setText(f"🛑 Processus {pid} terminé.")
                    self.refresh()
                except Exception as e:
                    self.status.setText(f"❌ Erreur : {e}")
        else:
            self.status.setText("⚠️ Aucun processus sélectionné.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaskManager()
    window.show()
    sys.exit(app.exec_())