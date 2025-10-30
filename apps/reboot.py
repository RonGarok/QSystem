#!/usr/bin/env python3
"""
reboot.py
- arrête les processus dont le nom ou la ligne de commande contient "Mendel" (insensible à la casse)
- remonte d'un dossier (project_root)
- entre dans ./boot et exécute boot.py avec le même interpréteur
- se termine après avoir démarré boot.py en détaché
"""

import os
import sys
import time
import subprocess
import platform

TARGET_TOKEN = "mendel"
BOOT_DIR_NAME = "boot"
BOOT_SCRIPT = "boot.py"
GRACE_PERIOD = 5.0  # secondes pour laisser le processus se terminer proprement

def kill_processes_with_token(token):
    token = token.lower()
    sent_any = False

    # Tentative avec psutil si disponible pour une fermeture propre
    try:
        import psutil
    except Exception:
        psutil = None

    if psutil:
        procs = []
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                cmdline = " ".join(info.get("cmdline") or []).lower()
                if token in name or token in cmdline:
                    try:
                        proc.terminate()
                        procs.append(proc)
                        sent_any = True
                    except Exception:
                        try:
                            proc.kill()
                            sent_any = True
                        except Exception:
                            pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if procs:
            gone, alive = psutil.wait_procs(procs, timeout=GRACE_PERIOD)
            # pour les restants, forcer
            for p in alive:
                try:
                    p.kill()
                except Exception:
                    pass
            return sent_any

    # Fallback sans psutil
    system = platform.system()
    if system == "Windows":
        # Utiliser tasklist pour récupérer les PID dont la ligne correspond, puis taskkill
        try:
            # Récupérer la liste des processus
            out = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], universal_newlines=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                # CSV fields: "Image Name","PID","Session Name","Session#","Mem Usage"
                parts = [p.strip('"') for p in line.split('","') if p]
                if not parts:
                    continue
                image = parts[0].lower()
                pid = parts[1] if len(parts) > 1 else None
                if token in image:
                    if pid and pid.isdigit():
                        try:
                            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            sent_any = True
                        except Exception:
                            pass
            # tentative additionnelle: pkill via wsl si disponible n'est pas utilisée
        except Exception:
            pass
    else:
        # Unix-like : pkill -f pour rechercher dans la ligne de commande
        try:
            subprocess.run(["pkill", "-f", token], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.1)
            # forcer les résistants
            subprocess.run(["pkill", "-9", "-f", token], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            sent_any = True
        except Exception:
            pass

    return sent_any

def main():
    cwd = os.path.abspath(os.path.dirname(__file__))
    print("reboot.py: répertoire du script :", cwd)

    print(f"reboot.py: arrêt des processus contenant le token '{TARGET_TOKEN}' (insensible à la casse)")
    sent = kill_processes_with_token(TARGET_TOKEN)
    if sent:
        print("reboot.py: signaux envoyés, attente pour fermeture...")
        time.sleep(GRACE_PERIOD)
    else:
        print("reboot.py: aucun processus ciblé trouvé ou impossibilité d'envoyer des signaux")

    # Remonter d'un dossier pour atteindre project_root
    project_root = os.path.abspath(os.path.join(cwd, ".."))
    print("reboot.py: changement vers project_root :", project_root)
    if not os.path.isdir(project_root):
        print("reboot.py: project_root introuvable, sortie avec erreur")
        sys.exit(1)
    os.chdir(project_root)

    # Descendre dans boot et exécuter boot.py
    boot_dir = os.path.join(project_root, BOOT_DIR_NAME)
    boot_script_path = os.path.join(boot_dir, BOOT_SCRIPT)
    if not os.path.isdir(boot_dir):
        print(f"reboot.py: dossier '{BOOT_DIR_NAME}' introuvable sous project_root, sortie")
        sys.exit(1)
    if not os.path.isfile(boot_script_path):
        print(f"reboot.py: '{BOOT_SCRIPT}' introuvable dans {boot_dir}, sortie")
        sys.exit(1)

    print(f"reboot.py: lancement de {boot_script_path} avec l'interpréteur {sys.executable}")
    try:
        # Lancer boot.py détaché. Sur Unix le double-fork est géré par la façon dont le système gère les processus enfant.
        if platform.system() == "Windows":
            # CREATE_NEW_PROCESS_GROUP aide au détachement sur Windows
            subprocess.Popen([sys.executable, boot_script_path], cwd=boot_dir,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen([sys.executable, boot_script_path], cwd=boot_dir,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        print("reboot.py: boot.py lancé en détaché. reboot.py va se terminer.")
    except Exception as e:
        print("reboot.py: échec lors du lancement de boot.py :", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
