import os
import shutil
import subprocess
import winreg
import time
from pathlib import Path
from typing import List, Dict, Optional
from misc.SystemRequests import SystemRequests
from misc.Logger import log_success, log_info, log_warning, log_error, log_progress, log_header
from misc.InstallationTracker import get_installation_tracker


class SunshineAIOUninstaller:
    """
    Gestionnaire de désinstallation complet pour Sunshine-AIO.
    
    Attributes
    ----------
    sr: SystemRequests
        Instance du gestionnaire des requêtes système.
    components: Dict
        Dictionnaire des composants à désinstaller.
    """

    def __init__(self, system_requests: SystemRequests) -> None:
        self._sr = system_requests
        self._tracker = get_installation_tracker(system_requests._base_path)
        self._components = {
            "sunshine": {
                "name": "Sunshine",
                "uninstaller_method": self._uninstall_sunshine_advanced,
                "verification_method": self._verify_sunshine_uninstalled
            },
            "virtual_display_driver": {
                "name": "Virtual Display Driver",
                "uninstaller_method": self._uninstall_vdd_advanced,
                "verification_method": self._verify_vdd_uninstalled
            },
            "sunshine_virtual_monitor": {
                "name": "Sunshine Virtual Monitor",
                "uninstaller_method": self._uninstall_svm_advanced,
                "verification_method": self._verify_svm_uninstalled
            },
            "playnite": {
                "name": "Playnite",
                "uninstaller_method": self._uninstall_playnite_advanced,
                "verification_method": self._verify_playnite_uninstalled
            },
            "playnite_watcher": {
                "name": "Playnite Watcher",
                "uninstaller_method": self._uninstall_playnite_watcher_advanced,
                "verification_method": self._verify_playnite_watcher_uninstalled
            },
            "multi_monitor_tool": {
                "name": "Multi Monitor Tool",
                "uninstaller_method": self._uninstall_mmt_advanced,
                "verification_method": self._verify_mmt_uninstalled
            },
            "vsync_toggle": {
                "name": "VSync Toggle",
                "uninstaller_method": self._uninstall_vsync_advanced,
                "verification_method": self._verify_vsync_uninstalled
            }
        }

    @property
    def sr(self):
        return self._sr

    @sr.setter
    def sr(self):
        raise ValueError("No manual edit allowed.")

    @property
    def components(self):
        return self._components

    @components.setter
    def components(self):
        raise ValueError("No manual edit allowed.")

    def uninstall_all(self, confirm: bool = True) -> bool:
        """
        Désinstalle tous les composants Sunshine-AIO.
        
        Parameters
        ----------
        confirm: bool
            Demander confirmation avant désinstallation.
            
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        if confirm:
            print("Cette opération va complètement supprimer tous les composants Sunshine-AIO de votre système.")
            print("Composants qui seront supprimés:")
            for component in self._components.values():
                print(f"  - {component['name']}")
            
            print("\n" + "="*50)
            response = input("Voulez-vous continuer? (oui/non): ").lower().strip()
            if response not in ['oui', 'o', 'yes', 'y']:
                print("Désinstallation annulée.")
                return False

        print("\nDémarrage de la désinstallation complète...")
        success = True

        # Arrêter les processus et services en premier
        self._stop_all_processes()
        self._stop_all_services()

        # Désinstaller chaque composant avec les nouvelles méthodes avancées
        for component_key, component in self._components.items():
            log_progress(f"Désinstallation de {component['name']}...")
            try:
                if component.get('uninstaller_method'):
                    if component['uninstaller_method']():
                        log_success(f"{component['name']} désinstallé avec succès")
                        # Supprimer le suivi d'installation
                        self._tracker.remove_installation_tracking(component_key)
                    else:
                        log_warning(f"Problèmes lors de la désinstallation de {component['name']}")
                        success = False
                else:
                    log_warning(f"Méthode de désinstallation non définie pour {component['name']}")
                    success = False
            except Exception as e:
                log_error(f"Erreur lors de la désinstallation de {component['name']}: {e}")
                success = False

        # Nettoyer les règles du pare-feu Windows
        self._cleanup_firewall_rules()

        # Nettoyer les entrées de démarrage
        self._cleanup_startup_entries()

        print(f"\nDésinstallation {'terminée' if success else 'terminée avec des avertissements'}!")
        if not success:
            print("Certains composants peuvent nécessiter un nettoyage manuel ou un redémarrage du système.")

        return success

    def uninstall_component(self, component_name: str) -> bool:
        """
        Désinstalle un composant spécifique.
        
        Parameters
        ----------
        component_name: str
            Le nom du composant à désinstaller.
            
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        component_key = component_name.lower().replace(" ", "_").replace("-", "_")

        if component_key not in self._components:
            log_error(f"Composant inconnu: {component_name}")
            return False

        component = self._components[component_key]
        log_progress(f"Désinstallation de {component['name']}...")

        try:
            if component.get('uninstaller_method'):
                success = component['uninstaller_method']()
                if success:
                    log_success(f"{component['name']} désinstallé avec succès")
                    # Supprimer le suivi d'installation
                    self._tracker.remove_installation_tracking(component_key)
                    return True
                else:
                    log_error(f"Échec de la désinstallation de {component['name']}")
                    return False
            else:
                log_error(f"Méthode de désinstallation non définie pour {component['name']}")
                return False
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation de {component['name']}: {e}")
            return False

    def _remove_files_and_directories(self, paths: List[str]) -> bool:
        """
        Supprime une liste de fichiers et répertoires.
        
        Parameters
        ----------
        paths: List[str]
            Liste des chemins à supprimer.
            
        Returns
        -------
        bool
            True si tous les éléments ont été supprimés avec succès.
        """
        success = True
        
        for path in paths:
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        log_success(f"Répertoire supprimé: {path}")
                    else:
                        os.remove(path)
                        log_success(f"Fichier supprimé: {path}")
                except Exception as e:
                    log_error(f"Échec de la suppression de {path}: {e}")
                    success = False
            else:
                log_info(f"Chemin inexistant (déjà supprimé): {path}")
        
        return success

    def _stop_all_processes(self):
        """Arrête tous les processus connus."""
        all_processes = []
        for component in self._components.values():
            if 'processes' in component:
                all_processes.extend(component['processes'])

        if all_processes:
            self._stop_processes(all_processes)

    def _stop_all_services(self):
        """Arrête tous les services connus."""
        all_services = []
        for component in self._components.values():
            if 'services' in component:
                all_services.extend(component['services'])

        if all_services:
            self._stop_services(all_services)

    def _stop_processes(self, processes: List[str]) -> bool:
        """
        Arrête les processus spécifiés.
        
        Parameters
        ----------
        processes: List[str]
            Liste des noms de processus à arrêter.
            
        Returns
        -------
        bool
            True si tous les processus ont été arrêtés avec succès.
        """
        success = True
        
        for process in processes:
            try:
                result = subprocess.run(['taskkill', '/F', '/IM', process], 
                                     capture_output=True, check=False)
                if result.returncode == 0:
                    log_success(f"Processus arrêté: {process}")
                else:
                    log_info(f"Processus {process} n'était pas en cours d'exécution")
            except Exception as e:
                log_warning(f"Erreur lors de l'arrêt du processus {process}: {e}")
                success = False
        
        return success

    def _stop_services(self, services: List[str]) -> bool:
        """
        Arrête et supprime les services spécifiés.
        
        Parameters
        ----------
        services: List[str]
            Liste des noms de services à arrêter et supprimer.
            
        Returns
        -------
        bool
            True si tous les services ont été supprimés avec succès.
        """
        success = True
        
        for service in services:
            try:
                # Arrêter le service
                stop_result = subprocess.run(['sc', 'stop', service], 
                                           capture_output=True, check=False)
                
                # Attendre un peu pour que le service s'arrête
                time.sleep(2)
                
                # Supprimer le service
                delete_result = subprocess.run(['sc', 'delete', service], 
                                             capture_output=True, check=False)
                
                if delete_result.returncode == 0:
                    log_success(f"Service arrêté et supprimé: {service}")
                else:
                    log_info(f"Service {service} n'existait pas ou était déjà supprimé")
                    
            except Exception as e:
                log_warning(f"Erreur lors de la suppression du service {service}: {e}")
                success = False
        
        return success

    def _remove_registry_keys(self, keys: List[str]) -> bool:
        """
        Supprime une liste de clés de registre.
        
        Parameters
        ----------
        keys: List[str]
            Liste des clés de registre à supprimer.
            
        Returns
        -------
        bool
            True si toutes les clés ont été supprimées avec succès.
        """
        success = True
        
        for key_path in keys:
            try:
                self._remove_registry_key(key_path)
                log_success(f"Clé de registre supprimée: {key_path}")
            except Exception as e:
                log_warning(f"Échec de la suppression de la clé de registre {key_path}: {e}")
                # Ne pas considérer comme un échec critique
        
        return success

    def _remove_registry_key(self, key_path: str):
        """
        Supprime une clé de registre.
        
        Parameters
        ----------
        key_path: str
            Chemin de la clé de registre à supprimer.
        """
        try:
            # Essayer HKEY_LOCAL_MACHINE d'abord
            try:
                winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                return
            except FileNotFoundError:
                pass

            # Essayer HKEY_CURRENT_USER
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
                return
            except FileNotFoundError:
                pass

        except Exception as e:
            raise e

    def _cleanup_firewall_rules(self):
        """Supprime les règles de pare-feu créées par Sunshine."""
        try:
            # Supprimer les règles de pare-feu Sunshine
            subprocess.run([
                'netsh', 'advfirewall', 'firewall', 'delete', 'rule', 
                'name=Sunshine'
            ], capture_output=True)
            print("  Règles de pare-feu nettoyées")
        except Exception:
            pass

    def _cleanup_startup_entries(self):
        """Supprime les entrées de démarrage."""
        startup_paths = [
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        ]

        startup_files = ["Sunshine.lnk", "Playnite.lnk", "PlayniteWatcher.lnk"]

        for startup_path in startup_paths:
            for startup_file in startup_files:
                file_path = os.path.join(startup_path, startup_file)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"  Entrée de démarrage supprimée: {startup_file}")
                    except Exception:
                        pass
    
    def _uninstall_svm_advanced(self) -> bool:
        """
        Méthode avancée de désinstallation de Sunshine Virtual Monitor.
        
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        log_info("Début de la désinstallation de Sunshine Virtual Monitor...")
        success = True
        
        try:
            # 1. Essayer d'abord le désinstalleur officiel (script)
            if self._find_and_run_official_uninstaller("sunshine_virtual_monitor"):
                log_success("Désinstallation via script officiel réussie")
                # Vérifier si tout a été supprimé
                if self._verify_svm_uninstalled():
                    log_success("Désinstallation de Sunshine Virtual Monitor terminée avec succès")
                    return True
                else:
                    log_info("Nettoyage des résidus après script officiel...")
            else:
                log_info("Aucun script de désinstallation trouvé, procédure manuelle...")
            
            # 2. Procédure manuelle si nécessaire
            # Supprimer les fichiers et dossiers
            files_to_remove = self._tracker.get_files_to_remove("sunshine_virtual_monitor")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("Désinstallation de Sunshine Virtual Monitor terminée avec succès")
            else:
                log_warning("Désinstallation de SVM terminée avec des avertissements")
            
            return success
            
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation de SVM: {e}")
            return False
    
    def _verify_svm_uninstalled(self) -> bool:
        """
        Vérifie que Sunshine Virtual Monitor a été correctement désinstallé.
        
        Returns
        -------
        bool
            True si SVM est complètement désinstallé.
        """
        for path in self._tracker.get_all_installation_paths("sunshine_virtual_monitor"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_playnite_advanced(self) -> bool:
        """
        Méthode avancée de désinstallation de Playnite.
        
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        log_info("Début de la désinstallation avancée de Playnite...")
        success = True
        
        try:
            # 1. Essayer d'abord le désinstalleur officiel
            if self._find_and_run_official_uninstaller("playnite"):
                log_success("Désinstallation via désinstalleur officiel réussie")
                # Vérifier si tout a été supprimé
                if self._verify_playnite_uninstalled():
                    log_success("Désinstallation de Playnite terminée avec succès")
                    return True
                else:
                    log_info("Nettoyage des résidus après désinstallation officielle...")
            else:
                log_info("Aucun désinstalleur officiel trouvé, procédure manuelle...")
            
            # 2. Procédure manuelle si nécessaire
            # Arrêter les processus Playnite
            processes = ["Playnite.DesktopApp.exe", "Playnite.FullscreenApp.exe", "Playnite.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 3. Supprimer les fichiers et dossiers restants
            files_to_remove = self._tracker.get_files_to_remove("playnite")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            # 4. Nettoyer le registre
            registry_keys = self._tracker.get_registry_keys("playnite")
            if registry_keys and not self._remove_registry_keys(registry_keys):
                success = False
            
            if success:
                log_success("Désinstallation de Playnite terminée avec succès")
            else:
                log_warning("Désinstallation de Playnite terminée avec des avertissements")
            
            return success
            
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation de Playnite: {e}")
            return False
    
    def _verify_playnite_uninstalled(self) -> bool:
        """
        Vérifie que Playnite a été correctement désinstallé.
        
        Returns
        -------
        bool
            True si Playnite est complètement désinstallé.
        """
        for path in self._tracker.get_all_installation_paths("playnite"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_playnite_watcher_advanced(self) -> bool:
        """
        Méthode avancée de désinstallation de Playnite Watcher.
        
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        log_info("Début de la désinstallation de Playnite Watcher...")
        success = True
        
        try:
            # 1. Arrêter le processus
            processes = ["PlayniteWatcher.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 2. Supprimer les fichiers et dossiers
            files_to_remove = self._tracker.get_files_to_remove("playnite_watcher")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("Désinstallation de Playnite Watcher terminée avec succès")
            else:
                log_warning("Désinstallation de Playnite Watcher terminée avec des avertissements")
            
            return success
            
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation de Playnite Watcher: {e}")
            return False
    
    def _verify_playnite_watcher_uninstalled(self) -> bool:
        """
        Vérifie que Playnite Watcher a été correctement désinstallé.
        
        Returns
        -------
        bool
            True si Playnite Watcher est complètement désinstallé.
        """
        for path in self._tracker.get_all_installation_paths("playnite_watcher"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_mmt_advanced(self) -> bool:
        """
        Méthode avancée de désinstallation de Multi Monitor Tool.
        
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        log_info("Début de la désinstallation de Multi Monitor Tool...")
        success = True
        
        try:
            # 1. Arrêter le processus
            processes = ["MultiMonitorTool.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 2. Supprimer les fichiers et dossiers
            files_to_remove = self._tracker.get_files_to_remove("multi_monitor_tool")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("Désinstallation de Multi Monitor Tool terminée avec succès")
            else:
                log_warning("Désinstallation de Multi Monitor Tool terminée avec des avertissements")
            
            return success
            
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation de Multi Monitor Tool: {e}")
            return False
    
    def _verify_mmt_uninstalled(self) -> bool:
        """
        Vérifie que Multi Monitor Tool a été correctement désinstallé.
        
        Returns
        -------
        bool
            True si MMT est complètement désinstallé.
        """
        for path in self._tracker.get_all_installation_paths("multi_monitor_tool"):
            if os.path.exists(path):
                return False
        return True
    
    def _uninstall_vsync_advanced(self) -> bool:
        """
        Méthode avancée de désinstallation de VSync Toggle.
        
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        log_info("Début de la désinstallation de VSync Toggle...")
        success = True
        
        try:
            # 1. Arrêter le processus
            processes = ["VSync Toggle.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 2. Supprimer les fichiers et dossiers
            files_to_remove = self._tracker.get_files_to_remove("vsync_toggle")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            if success:
                log_success("Désinstallation de VSync Toggle terminée avec succès")
            else:
                log_warning("Désinstallation de VSync Toggle terminée avec des avertissements")
            
            return success
            
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation de VSync Toggle: {e}")
            return False
    
    def _verify_vsync_uninstalled(self) -> bool:
        """
        Vérifie que VSync Toggle a été correctement désinstallé.
        
        Returns
        -------
        bool
            True si VSync Toggle est complètement désinstallé.
        """
        for path in self._tracker.get_all_installation_paths("vsync_toggle"):
            if os.path.exists(path):
                return False
        return True
    
    # =================== MÉTHODES UTILITAIRES ===================
    
    def _find_and_run_official_uninstaller(self, tool_name: str) -> bool:
        """
        Recherche et exécute le désinstalleur officiel d'un outil.
        
        Parameters
        ----------
        tool_name: str
            Nom de l'outil (sunshine, playnite, etc.)
            
        Returns
        -------
        bool
            True si un désinstalleur officiel a été trouvé et exécuté avec succès.
        """
        log_info(f"Recherche du désinstalleur officiel pour {tool_name}...")
        
        # Chemins d'installation possibles depuis le tracker
        install_paths = self._tracker.get_all_installation_paths(tool_name)
        
        # Définir les patterns de désinstalleurs selon l'outil
        uninstaller_patterns = {
            "sunshine": ["Uninstall.exe", "unins000.exe", "uninstall.exe"],
            "playnite": ["unins000.exe", "Uninstall.exe", "uninstall.exe"],
            "virtual_display_driver": [],  # Pas de désinstalleur standard
            "sunshine_virtual_monitor": ["uninstall.bat", "teardown_sunvdm.ps1"],
            "playnite_watcher": [],  # Pas de désinstalleur standard
            "multi_monitor_tool": [],  # Outil portable
            "vsync_toggle": []  # Outil portable
        }
        
        patterns = uninstaller_patterns.get(tool_name, [])
        if not patterns:
            log_info(f"Aucun désinstalleur officiel connu pour {tool_name}")
            return False
        
        # Rechercher dans les chemins d'installation
        for install_path in install_paths:
            if not os.path.exists(install_path):
                continue
                
            for pattern in patterns:
                uninstaller_path = os.path.join(install_path, pattern)
                if os.path.exists(uninstaller_path):
                    log_progress(f"Désinstalleur officiel trouvé: {uninstaller_path}")
                    return self._execute_official_uninstaller(uninstaller_path, tool_name)
        
        # Rechercher dans le registre Windows pour les programmes installés
        return self._find_uninstaller_in_registry(tool_name)
    
    def _execute_official_uninstaller(self, uninstaller_path: str, tool_name: str) -> bool:
        """
        Exécute un désinstalleur officiel.
        
        Parameters
        ----------
        uninstaller_path: str
            Chemin vers le désinstalleur
        tool_name: str
            Nom de l'outil
            
        Returns
        -------
        bool
            True si l'exécution s'est bien passée.
        """
        try:
            log_progress(f"Exécution du désinstalleur officiel: {uninstaller_path}")
            
            # Différents arguments selon le type de fichier
            if uninstaller_path.endswith('.exe'):
                # Arguments silencieux courants
                silent_args = ["/S", "/SILENT", "/VERYSILENT", "/QUIET", "/q"]
                
                # Essayer avec les arguments silencieux
                for arg in silent_args:
                    try:
                        result = subprocess.run(
                            [uninstaller_path, arg], 
                            timeout=120, 
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            log_success(f"Désinstalleur officiel exécuté avec succès (argument: {arg})")
                            return True
                    except subprocess.TimeoutExpired:
                        log_warning(f"Timeout lors de l'exécution avec l'argument {arg}")
                        continue
                    except Exception:
                        continue
                
                # Si aucun argument silencieux ne fonctionne, essayer sans argument
                try:
                    result = subprocess.run(
                        [uninstaller_path], 
                        timeout=180, 
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        log_success("Désinstalleur officiel exécuté avec succès")
                        return True
                    else:
                        log_warning(f"Le désinstalleur a retourné le code: {result.returncode}")
                        return False
                except subprocess.TimeoutExpired:
                    log_error("Timeout lors de l'exécution du désinstalleur")
                    return False
                    
            elif uninstaller_path.endswith('.bat'):
                # Script batch
                result = subprocess.run(
                    [uninstaller_path], 
                    cwd=os.path.dirname(uninstaller_path),
                    timeout=60, 
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    log_success("Script de désinstallation exécuté avec succès")
                    return True
                else:
                    log_warning(f"Le script a retourné le code: {result.returncode}")
                    return False
                    
            elif uninstaller_path.endswith('.ps1'):
                # Script PowerShell
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", uninstaller_path], 
                    cwd=os.path.dirname(uninstaller_path),
                    timeout=60, 
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    log_success("Script PowerShell de désinstallation exécuté avec succès")
                    return True
                else:
                    log_warning(f"Le script PowerShell a retourné le code: {result.returncode}")
                    return False
            
            return False
            
        except Exception as e:
            log_error(f"Erreur lors de l'exécution du désinstalleur officiel: {e}")
            return False
    
    def _find_uninstaller_in_registry(self, tool_name: str) -> bool:
        """
        Recherche un désinstalleur dans le registre Windows.
        
        Parameters
        ----------
        tool_name: str
            Nom de l'outil
            
        Returns
        -------
        bool
            True si un désinstalleur a été trouvé et exécuté.
        """
        try:
            # Mapping des noms d'outils vers les noms de programmes dans le registre
            registry_names = {
                "sunshine": ["Sunshine", "LizardByte Sunshine"],
                "playnite": ["Playnite"],
                "virtual_display_driver": ["Virtual Display Driver", "IDD Sample Driver"],
            }
            
            names_to_search = registry_names.get(tool_name, [])
            if not names_to_search:
                return False
            
            # Clés de registre à vérifier
            registry_keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            ]
            
            for hkey, subkey_path in registry_keys:
                try:
                    with winreg.OpenKey(hkey, subkey_path) as key:
                        # Énumérer toutes les sous-clés
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        
                                        # Vérifier si c'est notre programme
                                        for name in names_to_search:
                                            if name.lower() in display_name.lower():
                                                try:
                                                    uninstall_string = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                                    if uninstall_string:
                                                        log_progress(f"Désinstalleur trouvé dans le registre: {uninstall_string}")
                                                        return self._execute_registry_uninstaller(uninstall_string, tool_name)
                                                except FileNotFoundError:
                                                    continue
                                    except FileNotFoundError:
                                        continue
                                i += 1
                            except OSError:
                                break
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            log_warning(f"Erreur lors de la recherche dans le registre: {e}")
            return False
    
    def _execute_registry_uninstaller(self, uninstall_string: str, tool_name: str) -> bool:
        """
        Exécute une commande de désinstallation depuis le registre.
        
        Parameters
        ----------
        uninstall_string: str
            Commande de désinstallation depuis le registre
        tool_name: str
            Nom de l'outil
            
        Returns
        -------
        bool
            True si l'exécution s'est bien passée.
        """
        try:
            # Parser la commande (peut contenir des guillemets et arguments)
            import shlex
            
            # Nettoyer et parser la commande
            if uninstall_string.startswith('"'):
                # Commande avec guillemets
                parts = shlex.split(uninstall_string)
            else:
                # Commande simple
                parts = uninstall_string.split()
            
            if not parts:
                return False
            
            # Ajouter des arguments silencieux si possible
            if parts[0].lower().endswith('.exe'):
                # Essayer avec des arguments silencieux
                for silent_arg in ['/S', '/SILENT', '/VERYSILENT', '/QUIET']:
                    try:
                        cmd = parts + [silent_arg]
                        result = subprocess.run(cmd, timeout=120, capture_output=True)
                        if result.returncode == 0:
                            log_success(f"Désinstallation via registre réussie avec {silent_arg}")
                            return True
                    except Exception:
                        continue
            
            # Exécuter la commande telle quelle en dernier recours
            result = subprocess.run(parts, timeout=180, capture_output=True)
            if result.returncode == 0:
                log_success("Désinstallation via registre réussie")
                return True
            else:
                log_warning(f"La commande de désinstallation a retourné le code: {result.returncode}")
                return False
            
        except Exception as e:
            log_error(f"Erreur lors de l'exécution de la commande de désinstallation: {e}")
            return False
    
    def _cleanup_sunshine_firewall_rules(self) -> bool:
        """
        Supprime les règles de pare-feu créées par Sunshine.
        
        Returns
        -------
        bool
            True si toutes les règles ont été supprimées avec succès.
        """
        try:
            # Supprimer les règles de pare-feu Sunshine
            firewall_rules = ["Sunshine", "sunshine.exe"]
            
            for rule in firewall_rules:
                result = subprocess.run([
                    'netsh', 'advfirewall', 'firewall', 'delete', 'rule', 
                    f'name={rule}'
                ], capture_output=True)
                
                if result.returncode == 0:
                    log_success(f"Règle de pare-feu supprimée: {rule}")
                else:
                    log_info(f"Règle de pare-feu {rule} n'existait pas")
            
            return True
            
        except Exception as e:
            log_warning(f"Erreur lors du nettoyage des règles de pare-feu: {e}")
            return False
    
    def _cleanup_sunshine_startup_entries(self) -> bool:
        """
        Supprime les entrées de démarrage liées à Sunshine.
        
        Returns
        -------
        bool
            True si toutes les entrées ont été supprimées avec succès.
        """
        startup_paths = [
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"),
            "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        ]

        startup_files = ["Sunshine.lnk", "sunshine.lnk"]
        success = True

        for startup_path in startup_paths:
            for startup_file in startup_files:
                file_path = os.path.join(startup_path, startup_file)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        log_success(f"Entrée de démarrage supprimée: {startup_file}")
                    except Exception as e:
                        log_warning(f"Impossible de supprimer {startup_file}: {e}")
                        success = False
        
        return success
        
    @property
    def tracker(self):
        """Accès au tracker d'installation."""
        return self._tracker

    def list_installed_components(self) -> List[str]:
        """
        Liste les composants actuellement installés.
        
        Returns
        -------
        List[str]
            Liste des noms des composants installés.
        """
        installed = []

        for component_key, component in self._components.items():
            if self._tracker.is_tool_installed(component_key):
                installed.append(component['name'])

        return installed

    def generate_uninstall_report(self) -> str:
        """
        Génère un rapport de ce qui serait désinstallé.
        
        Returns
        -------
        str
            Rapport détaillé de désinstallation.
        """
        report = []
        report.append("=== RAPPORT DE DÉSINSTALLATION SUNSHINE-AIO ===")
        report.append("")
        
        # Utiliser le rapport du tracker d'installation
        report.append(self._tracker.get_installation_report())
        report.append("")
        report.append("DÉTAILS DE DÉSINSTALLATION:")
        report.append("")

        for component_key, component in self._components.items():
            if self._tracker.is_tool_installed(component_key):
                report.append(f"• {component['name'].upper()} - INSTALLÉ")
                
                # Chemins d'installation
                paths = self._tracker.get_all_installation_paths(component_key)
                if paths:
                    report.append("  Chemins à supprimer:")
                    for path in paths:
                        report.append(f"    - {path}")
                
                # Fichiers à supprimer
                files = self._tracker.get_files_to_remove(component_key)
                if files:
                    report.append("  Fichiers/Dossiers à supprimer:")
                    for file_path in files:
                        status = "EXISTE" if os.path.exists(file_path) else "INTROUVABLE"
                        report.append(f"    - {file_path} ({status})")
                
                # Services
                services = self._tracker.get_services_to_remove(component_key)
                if services:
                    report.append("  Services à supprimer:")
                    for service in services:
                        report.append(f"    - {service}")
                
                # Drivers
                drivers = self._tracker.get_drivers_to_remove(component_key)
                if drivers:
                    report.append("  Drivers à supprimer:")
                    for driver in drivers:
                        report.append(f"    - {driver}")
                
                # Clés de registre
                reg_keys = self._tracker.get_registry_keys(component_key)
                if reg_keys:
                    report.append("  Clés de registre à supprimer:")
                    for key in reg_keys:
                        report.append(f"    - {key}")
                
                report.append("")
            else:
                report.append(f"• {component['name'].upper()} - NON INSTALLÉ")
                report.append("")

        return "\n".join(report)
    
    # =================== MÉTHODES DE DÉSINSTALLATION AVANCÉES ===================
    
    def _uninstall_sunshine_advanced(self) -> bool:
        """
        Méthode avancée de désinstallation de Sunshine.
        
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        log_info("Début de la désinstallation avancée de Sunshine...")
        success = True
        
        try:
            # 1. Essayer d'abord le désinstalleur officiel
            if self._find_and_run_official_uninstaller("sunshine"):
                log_success("Désinstallation via désinstalleur officiel réussie")
                # Vérifier si tout a été supprimé
                if self._verify_sunshine_uninstalled():
                    log_success("Désinstallation de Sunshine terminée avec succès")
                    return True
                else:
                    log_info("Nettoyage des résidus après désinstallation officielle...")
            else:
                log_info("Aucun désinstalleur officiel trouvé, procédure manuelle...")
            
            # 2. Procédure manuelle si nécessaire
            # Arrêter les processus Sunshine
            processes = ["sunshine.exe", "sunshine_console.exe"]
            if not self._stop_processes(processes):
                success = False
            
            # 3. Arrêter et supprimer le service Sunshine
            services = self._tracker.get_services_to_remove("sunshine")
            if services and not self._stop_services(services):
                success = False
            
            # 4. Supprimer les fichiers et dossiers restants
            files_to_remove = self._tracker.get_files_to_remove("sunshine")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            # 5. Nettoyer le registre
            registry_keys = self._tracker.get_registry_keys("sunshine")
            if registry_keys and not self._remove_registry_keys(registry_keys):
                success = False
            
            # 6. Nettoyer les règles de pare-feu
            self._cleanup_sunshine_firewall_rules()
            
            # 7. Nettoyer les entrées de démarrage
            self._cleanup_sunshine_startup_entries()
            
            if success:
                log_success("Désinstallation de Sunshine terminée avec succès")
            else:
                log_warning("Désinstallation de Sunshine terminée avec des avertissements")
            
            return success
            
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation de Sunshine: {e}")
            return False
    
    def _verify_sunshine_uninstalled(self) -> bool:
        """
        Vérifie que Sunshine a été correctement désinstallé.
        
        Returns
        -------
        bool
            True si Sunshine est complètement désinstallé.
        """
        # Vérifier les chemins d'installation
        for path in self._tracker.get_all_installation_paths("sunshine"):
            if os.path.exists(path):
                return False
        
        # Vérifier les clés de registre
        for key in self._tracker.get_registry_keys("sunshine"):
            if self._tracker._check_registry_key_exists(key):
                return False
        
        return True
    
    def _uninstall_vdd_advanced(self) -> bool:
        """
        Méthode avancée de désinstallation du Virtual Display Driver.
        
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        log_info("Début de la désinstallation avancée du Virtual Display Driver...")
        success = True
        
        try:
            # 1. Désinstaller le driver via Device Manager
            log_progress("Désinstallation du driver depuis le gestionnaire de périphériques...")
            try:
                result = subprocess.run([
                    'pnputil', '/disable-device', '/deviceid', 'root\\iddsampledriver'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    log_success("Driver désactivé avec succès")
                else:
                    log_warning("Impossible de désactiver le driver")
            except Exception as e:
                log_warning(f"Erreur lors de la désactivation du driver: {e}")
            
            # 2. Supprimer le driver du driver store
            log_progress("Suppression du driver du driver store...")
            try:
                # Lister les drivers pour trouver iddsampledriver
                result = subprocess.run(['pnputil', '/enum-drivers'], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    published_name = None
                    
                    for i, line in enumerate(lines):
                        if 'iddsampledriver.inf' in line.lower():
                            # Rechercher le nom publié dans les lignes précédentes
                            for j in range(max(0, i-10), i):
                                if 'published name' in lines[j].lower():
                                    published_name = lines[j].split(':')[-1].strip()
                                    break
                            break
                    
                    if published_name:
                        log_progress(f"Suppression du driver {published_name}...")
                        result = subprocess.run([
                            'pnputil', '/delete-driver', published_name, '/uninstall'
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            log_success(f"Driver {published_name} supprimé avec succès")
                        else:
                            log_warning(f"Impossible de supprimer le driver {published_name}")
                            success = False
                    else:
                        log_warning("Driver iddsampledriver.inf non trouvé dans le driver store")
                        
            except Exception as e:
                log_error(f"Erreur lors de la suppression du driver: {e}")
                success = False
            
            # 3. Supprimer les fichiers d'installation
            files_to_remove = self._tracker.get_files_to_remove("virtual_display_driver")
            if files_to_remove and not self._remove_files_and_directories(files_to_remove):
                success = False
            
            # 4. Nettoyer le registre
            registry_keys = self._tracker.get_registry_keys("virtual_display_driver")
            if registry_keys and not self._remove_registry_keys(registry_keys):
                success = False
            
            if success:
                log_success("Désinstallation du Virtual Display Driver terminée avec succès")
            else:
                log_warning("Désinstallation du VDD terminée avec des avertissements")
            
            return success
            
        except Exception as e:
            log_error(f"Erreur lors de la désinstallation du VDD: {e}")
            return False
    
    def _verify_vdd_uninstalled(self) -> bool:
        """
        Vérifie que le Virtual Display Driver a été correctement désinstallé.
        
        Returns
        -------
        bool
            True si le VDD est complètement désinstallé.
        """
        # Vérifier les fichiers d'installation
        for path in self._tracker.get_all_installation_paths("virtual_display_driver"):
            if os.path.exists(path):
                return False
        
        # Vérifier dans le driver store
        try:
            result = subprocess.run(['pnputil', '/enum-drivers'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and 'iddsampledriver.inf' in result.stdout.lower():
                return False
        except Exception:
            pass
        
        return True