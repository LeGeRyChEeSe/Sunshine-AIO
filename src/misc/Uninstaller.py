import os
import shutil
import subprocess
import winreg
from pathlib import Path
from typing import List, Dict, Optional
from misc.SystemRequests import SystemRequests


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
        self._components = {
            "sunshine": {
                "name": "Sunshine",
                "paths": [
                    os.path.expanduser("~\\AppData\\Local\\LizardByte\\Sunshine"),
                    "C:\\Program Files\\Sunshine",
                    "C:\\Program Files (x86)\\Sunshine"
                ],
                "registry_keys": [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Sunshine",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Sunshine"
                ],
                "services": ["SunshineService"],
                "processes": ["sunshine.exe"]
            },
            "virtual_display_driver": {
                "name": "Virtual Display Driver",
                "paths": [
                    "C:\\IddSampleDriver"
                ],
                "driver_cleanup": True,
                "device_manager_cleanup": True
            },
            "sunshine_virtual_monitor": {
                "name": "Sunshine Virtual Monitor",
                "paths": [
                    os.path.expanduser("~\\AppData\\Local\\SunshineVirtualMonitor"),
                    os.path.expanduser("~\\Documents\\SunshineVirtualMonitor")
                ]
            },
            "playnite": {
                "name": "Playnite",
                "paths": [
                    os.path.expanduser("~\\AppData\\Local\\Playnite"),
                    os.path.expanduser("~\\AppData\\Roaming\\Playnite"),
                    "C:\\Program Files\\Playnite",
                    "C:\\Program Files (x86)\\Playnite"
                ],
                "registry_keys": [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Playnite",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Playnite"
                ],
                "processes": ["Playnite.exe", "PlayniteUI.exe"]
            },
            "playnite_watcher": {
                "name": "Playnite Watcher",
                "paths": [
                    os.path.expanduser("~\\AppData\\Local\\PlayniteWatcher"),
                    os.path.expanduser("~\\Documents\\PlayniteWatcher")
                ],
                "processes": ["PlayniteWatcher.exe"]
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

        # Désinstaller chaque composant
        for component_key, component in self._components.items():
            print(f"\nDésinstallation de {component['name']}...")
            if not self._uninstall_component(component):
                print(f"Attention: Des problèmes sont survenus lors de la désinstallation de {component['name']}")
                success = False
            else:
                print(f"✓ {component['name']} désinstallé avec succès")

        # Traitement spécial pour le Virtual Display Driver
        if not self._uninstall_virtual_display_driver():
            print("Attention: Le Virtual Display Driver peut nécessiter une suppression manuelle depuis le Gestionnaire de périphériques")
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
            print(f"Composant inconnu: {component_name}")
            return False

        component = self._components[component_key]
        print(f"Désinstallation de {component['name']}...")

        # Arrêter les processus et services associés
        if 'processes' in component:
            self._stop_processes(component['processes'])
        if 'services' in component:
            self._stop_services(component['services'])

        return self._uninstall_component(component)

    def _uninstall_component(self, component: Dict) -> bool:
        """
        Désinstalle un composant individuel.
        
        Parameters
        ----------
        component: Dict
            Dictionnaire contenant les informations du composant.
            
        Returns
        -------
        bool
            True si la désinstallation s'est bien passée.
        """
        success = True

        # Supprimer les répertoires
        if 'paths' in component:
            for path in component['paths']:
                if os.path.exists(path):
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                            print(f"  Répertoire supprimé: {path}")
                        else:
                            os.remove(path)
                            print(f"  Fichier supprimé: {path}")
                    except Exception as e:
                        print(f"  Échec de la suppression de {path}: {e}")
                        success = False

        # Supprimer les clés de registre
        if 'registry_keys' in component:
            for reg_key in component['registry_keys']:
                try:
                    self._remove_registry_key(reg_key)
                    print(f"  Clé de registre supprimée: {reg_key}")
                except Exception as e:
                    print(f"  Échec de la suppression de la clé de registre {reg_key}: {e}")

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

    def _stop_processes(self, processes: List[str]):
        """
        Arrête les processus spécifiés.
        
        Parameters
        ----------
        processes: List[str]
            Liste des noms de processus à arrêter.
        """
        for process in processes:
            try:
                result = subprocess.run(['taskkill', '/F', '/IM', process], 
                                     capture_output=True, check=False)
                if result.returncode == 0:
                    print(f"  Processus arrêté: {process}")
            except Exception:
                pass

    def _stop_services(self, services: List[str]):
        """
        Arrête les services spécifiés.
        
        Parameters
        ----------
        services: List[str]
            Liste des noms de services à arrêter.
        """
        for service in services:
            try:
                # Arrêter le service
                subprocess.run(['sc', 'stop', service], 
                             capture_output=True, check=False)
                # Supprimer le service
                subprocess.run(['sc', 'delete', service], 
                             capture_output=True, check=False)
                print(f"  Service arrêté et supprimé: {service}")
            except Exception:
                pass

    def _uninstall_virtual_display_driver(self) -> bool:
        """
        Traitement spécial pour la suppression du Virtual Display Driver.
        
        Returns
        -------
        bool
            True si la suppression s'est bien passée.
        """
        try:
            # Essayer de désinstaller avec pnputil
            result = subprocess.run([
                'pnputil', '/delete-driver', 'IddSampleDriver.inf', '/uninstall'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("  ✓ Virtual Display Driver supprimé avec succès")
                return True
            else:
                print("  Échec de la suppression du driver, nettoyage manuel nécessaire dans le Gestionnaire de périphériques")
                print("  Veuillez supprimer manuellement 'IDD Sample Driver' depuis le Gestionnaire de périphériques")
                return False
        except Exception as e:
            print(f"  Erreur lors de la suppression du driver: {e}")
            return False

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
            if 'paths' in component:
                for path in component['paths']:
                    if os.path.exists(path):
                        installed.append(component['name'])
                        break

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
        report.append("Rapport de Désinstallation Sunshine-AIO")
        report.append("=" * 40)
        report.append("")

        for component_key, component in self._components.items():
            report.append(f"{component['name']}:")

            if 'paths' in component:
                report.append("  Répertoires/Fichiers à supprimer:")
                for path in component['paths']:
                    status = "EXISTE" if os.path.exists(path) else "INTROUVABLE"
                    report.append(f"    - {path} ({status})")

            if 'processes' in component:
                report.append("  Processus à arrêter:")
                for process in component['processes']:
                    report.append(f"    - {process}")

            if 'services' in component:
                report.append("  Services à supprimer:")
                for service in component['services']:
                    report.append(f"    - {service}")

            if 'registry_keys' in component:
                report.append("  Clés de registre à supprimer:")
                for key in component['registry_keys']:
                    report.append(f"    - {key}")

            report.append("")

        return "\n".join(report)