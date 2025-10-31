#!/usr/bin/env python3
"""
reboot.py
- arrête les processus dont le nom ou la ligne de commande contient "mendel" (insensible à la casse)
- n'arrête jamais son propre processus ou les processus dont la cmdline contient exactement ce reboot.py
- remonte d'un dossier (project_root)
- entre dans ./boot et exécute boot.py avec le même interpréteur
- consigne tout le texte de la console dans rebootlog.txt
- lance boot.py en détaché et se termine
"""

import os
import sys
import time
import subprocess
import platform
import logging

TARGET_TOKEN = "mendel"
BOOT_DIR_NAME = "boot"
BOOT_SCRIPT = "boot.py"
GRACE_PERIOD = 5.0  # secondes pour laisser le processus se terminer proprement
LOG_FILENAME = "rebootlog.txt"

def setup_logger(log_path):
    logger = logging.getLogger("reboot")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger

def run_cmd_capture(cmd, logger):
    logger.debug("Exécution commande: %s", " ".join(cmd))
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        logger.debug("Commande réussite, sortie:\n%s", out.strip())
        return 0, out, ""
    except subprocess.CalledProcessError as e:
        logger.debug("Commande échouée (code %s), sortie:\n%s", e.returncode, (e.output or "").strip())
        return e.returncode, e.output or "", str(e)
    except Exception as e:
        logger.debug("Erreur lors de l'exécution de la commande: %s", e)
        return 1, "", str(e)

def should_ignore_process(pid, name, cmdline, script_path, logger):
    """
    True si on doit ignorer ce processus (par ex. c'est le script actuel).
    - ignore si pid == current pid
    - ignore si la cmdline contient exactement le chemin absolu du reboot.py
    - ignore si cmdline contient python interpreter + reboot.py comme script
    """
    try:
        cur_pid = os.getpid()
    except Exception:
        cur_pid = None

    if cur_pid is not None and pid == cur_pid:
        logger.debug("Ignoré: PID correspond au PID courant (%s).", pid)
        return True

    # Normaliser cmdline en string pour comparaison
    cmdline_str = ""
    try:
        if isinstance(cmdline, (list, tuple)):
            cmdline_str = " ".join(str(x) for x in cmdline)
        else:
            cmdline_str = str(cmdline)
    except Exception:
        cmdline_str = str(cmdline or "")

    # Comparaison chemin absolu du reboot.py
    try:
        script_path_norm = os.path.abspath(script_path)
        if script_path_norm and script_path_norm in cmdline_str:
            logger.debug("Ignoré: cmdline contient reboot.py (%s) pour PID %s.", script_path_norm, pid)
            return True
    except Exception:
        pass

    return False

def kill_processes_with_token(token, script_path, logger):
    token = token.lower()
    sent_any = False

    # Tentative avec psutil si disponible
    try:
        import psutil
    except Exception:
        psutil = None

    if psutil:
        logger.info("Utilisation de psutil pour rechercher des processus contenant '%s'", token)
        procs_to_wait = []
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                info = proc.info
                pid = info.get("pid")
                name = (info.get("name") or "").lower()
                cmdline_list = info.get("cmdline") or []
                cmdline_str = " ".join(str(x) for x in cmdline_list).lower()
                # Vérifier ignorés
                if should_ignore_process(pid, name, cmdline_list, script_path, logger):
                    continue
                if token in name or token in cmdline_str:
                    logger.info("Ciblé pour terminaison: PID %s, name=%s, cmdline=%s", pid, info.get("name"), info.get("cmdline"))
                    try:
                        proc.terminate()
                        procs_to_wait.append(proc)
                        sent_any = True
                    except Exception as e:
                        logger.warning("Impossible d'envoyer terminate à PID %s: %s", pid, e)
                        try:
                            proc.kill()
                            sent_any = True
                        except Exception as e2:
                            logger.warning("Impossible de kill PID %s: %s", pid, e2)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if procs_to_wait:
            logger.info("Attente de l'arrêt des processus (%.1f s)...", GRACE_PERIOD)
            gone, alive = psutil.wait_procs(procs_to_wait, timeout=GRACE_PERIOD)
            if alive:
                for p in alive:
                    try:
                        logger.info("Forcer kill PID %s", p.pid)
                        p.kill()
                    except Exception as e:
                        logger.warning("Échec kill PID %s: %s", getattr(p, "pid", "<?>"), e)
        return sent_any

    # Fallback sans psutil
    system = platform.system()
    logger.info("psutil non disponible, fallback plateforme: %s", system)
    if system == "Windows":
        code, out, err = run_cmd_capture(["tasklist", "/FO", "CSV", "/NH"], logger)
        if code == 0 and out:
            for line in out.splitlines():
                parts = [p.strip('"') for p in line.split('","') if p]
                if not parts:
                    continue
                image = parts[0].lower()
                pid = None
                if len(parts) > 1:
                    pid = parts[1]
                # on ne peut pas voir la cmdline complète via tasklist; n'arrêtons que si l'image contient token
                if pid and pid.isdigit():
                    try:
                        pid_int = int(pid)
                    except Exception:
                        pid_int = None
                else:
                    pid_int = None
                # Ici on n'a pas la cmdline, donc on vérifie image et on ignore le PID courant
                if pid_int is not None:
                    if pid_int == os.getpid():
                        logger.debug("Ignoré (tasklist): PID %s est le PID courant.", pid_int)
                        continue
                if token in image:
                    logger.info("Image correspondante trouvée: %s (PID %s)", parts[0], pid)
                    if pid and pid.isdigit():
                        run_cmd_capture(["taskkill", "/PID", pid, "/T", "/F"], logger)
                        sent_any = True
        else:
            logger.debug("Impossible d'obtenir la liste des processus via tasklist: %s", err)
    else:
        # Unix-like: pkill -f token, mais on veut éviter de pkill notre propre reboot.py.
        # Pour être sûr, on va lister avec ps aux et filtrer manuellement.
        try:
            out = subprocess.check_output(["ps", "axo", "pid=,args="], universal_newlines=True)
            for line in out.splitlines():
                if not line.strip():
                    continue
                # split once to separate pid from cmd
                try:
                    pid_str, cmd = line.strip().split(None, 1)
                except ValueError:
                    continue
                try:
                    pid_int = int(pid_str)
                except Exception:
                    continue
                cmd_lower = cmd.lower()
                # ignorer le processus courant et toute ligne contenant le chemin absolu du reboot.py
                if should_ignore_process(pid_int, None, cmd, script_path, logger):
                    continue
                if token in cmd_lower or token in (os.path.basename(cmd_lower)):
                    logger.info("Ciblé pour terminaison (ps): PID %s cmd=%s", pid_int, cmd)
                    try:
                        os.kill(pid_int, 15)  # SIGTERM
                        sent_any = True
                    except PermissionError:
                        logger.warning("Permission refusée pour kill PID %s", pid_int)
                    except ProcessLookupError:
                        pass
            # attendre un peu puis forcer les restants
            if sent_any:
                time.sleep(0.1)
                for line in out.splitlines():
                    if not line.strip():
                        continue
                    try:
                        pid_str, cmd = line.strip().split(None, 1)
                    except ValueError:
                        continue
                    try:
                        pid_int = int(pid_str)
                    except Exception:
                        continue
                    if should_ignore_process(pid_int, None, cmd, script_path, logger):
                        continue
                    # vérifier si le processus existe toujours et contient token
                    try:
                        with open(f"/proc/{pid_int}/cmdline", "r") as f:
                            cmdline_raw = f.read().replace("\x00", " ").lower()
                    except Exception:
                        cmdline_raw = cmd.lower()
                    if token in cmdline_raw:
                        try:
                            os.kill(pid_int, 9)  # SIGKILL
                            logger.info("Forcer kill PID %s", pid_int)
                        except Exception:
                            pass
        except Exception:
            # dernière tentative simple: pkill -f token en évitant notre propre script by excluding its PID
            try:
                # Construire une pkill, puis vérifier que nous ne tuons pas notre PID
                subprocess.run(["pkill", "-f", token], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.1)
                subprocess.run(["pkill", "-9", "-f", token], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                sent_any = True
            except Exception as e:
                logger.debug("Erreur tentative pkill: %s", e)

    return sent_any

def main():
    script_dir = os.path.abspath(os.path.dirname(__file__))
    script_path = os.path.abspath(__file__)
    log_path = os.path.join(script_dir, LOG_FILENAME)
    logger = setup_logger(log_path)

    logger.info("reboot.py démarré dans %s", script_dir)
    logger.info("Recherche et arrêt des processus contenant le token '%s' (insensible à la casse)", TARGET_TOKEN)

    try:
        sent = kill_processes_with_token(TARGET_TOKEN, script_path, logger)
        if sent:
            logger.info("Signaux envoyés, attente de %.1f secondes pour fermeture propre", GRACE_PERIOD)
            time.sleep(GRACE_PERIOD)
        else:
            logger.info("Aucun signal envoyé ou aucun processus trouvé contenant '%s'", TARGET_TOKEN)
    except Exception as e:
        logger.exception("Erreur lors de la tentative d'arrêt des processus: %s", e)

    # Remonter d'un dossier pour atteindre project_root
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    logger.info("Changement vers project_root (parent): %s", project_root)
    if not os.path.isdir(project_root):
        logger.error("project_root introuvable: %s", project_root)
        sys.exit(1)
    os.chdir(project_root)

    # Descendre dans boot et exécuter boot.py
    boot_dir = os.path.join(project_root, BOOT_DIR_NAME)
    boot_script_path = os.path.join(boot_dir, BOOT_SCRIPT)
    if not os.path.isdir(boot_dir):
        logger.error("Dossier '%s' introuvable sous project_root", BOOT_DIR_NAME)
        sys.exit(1)
    if not os.path.isfile(boot_script_path):
        logger.error("Fichier '%s' introuvable dans %s", BOOT_SCRIPT, boot_dir)
        sys.exit(1)

    logger.info("Lancement de %s avec l'interpréteur %s", boot_script_path, sys.executable)
    try:
        if platform.system() == "Windows":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            subprocess.Popen([sys.executable, boot_script_path],
                             cwd=boot_dir,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             creationflags=creationflags)
        else:
            subprocess.Popen([sys.executable, boot_script_path],
                             cwd=boot_dir,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
        logger.info("boot.py lancé en détaché. reboot.py va se terminer.")
    except Exception as e:
        logger.exception("Échec lors du lancement de boot.py: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
