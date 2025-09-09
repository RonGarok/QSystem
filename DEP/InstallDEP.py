import subprocess
import os
import sys

modules = ["PyQt5", "flask", "art", "psutil", "wmi"]

print("\n📦 Installation des dépendances manquantes :")
for module in modules:
    try:
        subprocess.check_call(["pip", "install", module])
        print(f"✅ {module} installé avec succès.")
    except Exception:
        print(f"❌ Échec d'installation pour {module}")

# 🚀 Lancer Startup.py après installation
startup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Startup", "Startup.py")
subprocess.Popen(["python", startup_path])

# 💥 Terminer proprement le script
sys.exit()