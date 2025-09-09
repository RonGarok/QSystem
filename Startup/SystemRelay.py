import platform
import os
import subprocess
import sys
import time
from art import tprint
import psutil
import wmi

def afficher_ascii():
    os.system("cls" if os.name == "nt" else "clear")
    tprint("SYSTEM RELAY")
    print("\n🔍 Collecte des informations système...\n")

def collecter_infos():
    c = wmi.WMI()
    infos = []

    # Carte mère
    for board in c.Win32_BaseBoard():
        infos.append(f"Carte mère : {board.Manufacturer} {board.Product}")

    # Processeur
    for cpu in c.Win32_Processor():
        infos.append(f"Processeur : {cpu.Name.strip()}")

    # RAM
    ram = round(psutil.virtual_memory().total / (1024**3), 2)
    infos.append(f"RAM : {ram} Go")

    # GPU
    for gpu in c.Win32_VideoController():
        infos.append(f"Carte graphique : {gpu.Name}")

    # Disque
    for disk in c.Win32_DiskDrive():
        try:
            size_gb = round(int(disk.Size) / (1024**3), 2)
            infos.append(f"Disque : {disk.Model} ({size_gb} Go)")
        except Exception as e:
            infos.append(f"Disque : {disk.Model} (taille inconnue)")

    # OS
    infos.append(f"Système : {platform.system()} {platform.release()} ({platform.version()})")

    return infos

def sauvegarder_infos(infos):
    chemin = os.path.join(os.path.dirname(__file__), "SystemInfo.txt")
    with open(chemin, "w", encoding="utf-8") as f:
        for ligne in infos:
            f.write(ligne + "\n")

def afficher_console(infos):
    for ligne in infos:
        print(f"🧩 {ligne}")
        time.sleep(0.5)

def lancer_system_start():
    print("\n⏳ Attente de 10 secondes avant lancement de SystemStart.py...\n")
    time.sleep(10)
    chemin = os.path.join(os.path.dirname(__file__), "SystemStart.py")
    subprocess.Popen(["python", chemin])
    sys.exit()

if __name__ == "__main__":
    afficher_ascii()
    infos = collecter_infos()
    sauvegarder_infos(infos)
    afficher_console(infos)
    lancer_system_start()