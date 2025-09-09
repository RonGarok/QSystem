import os
import sys
import subprocess
import ctypes
import importlib.util
import keyboard

# 🔐 Demande les droits admin
def demander_admin():
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    else:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

# 🛑 Bloque les raccourcis clavier
def bloquer_touches():
    touches = ['alt', 'ctrl', 'win', 'esc', 'tab', 'f4']
    for t in touches:
        keyboard.block_key(t)

# 📦 Vérifie les dépendances
def verifier_dependances():
    modules = {
        "PyQt5": "PyQt5",
        "Flask": "flask",
        "ASCII Art": "art",
        "Psutil": "psutil",
        "WMI": "wmi"
    }

    manquants = []

    print("\n📦 Vérification des dépendances :")
    for nom_affiche, nom_module in modules.items():
        spec = importlib.util.find_spec(nom_module)
        if spec is None:
            print(f"❌ {nom_affiche} ({nom_module}) n'est pas installé.")
            manquants.append(nom_module)
        else:
            try:
                mod = importlib.import_module(nom_module)
                version = getattr(mod, '__version__', 'Version inconnue')
                print(f"✅ {nom_affiche} installé — version : {version}")
            except Exception:
                print(f"✅ {nom_affiche} installé — version non détectée")

    # Vérifie pip
    try:
        pip_version = subprocess.check_output(["pip", "--version"]).decode().strip()
        print(f"\n🧪 pip : {pip_version}")
    except Exception:
        print("❌ pip non détecté")
        manquants.append("pip")

    return manquants

# 🚀 Lancer Startup.py
def lancer_startup():
    chemin = os.path.join(os.path.dirname(__file__), "Startup", "Startup.py")
    subprocess.Popen(["python", chemin])

# 🚨 Lancer InstallDEP.py
def lancer_install_dep():
    chemin_install = os.path.join(os.path.dirname(__file__), "DEP", "InstallDEP.py")
    subprocess.call(["python", chemin_install])

# 🧨 Main
if __name__ == "__main__":
    demander_admin()
    bloquer_touches()
    manquants = verifier_dependances()

    if not manquants:
        print("\n✅ Toutes les dépendances sont présentes. Lancement de Startup.py...")
        lancer_startup()
    else:
        print("\n⚠️ Dépendances manquantes détectées. Lancement de InstallDEP.py...")
        lancer_install_dep()

    # Garde la console active
    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass