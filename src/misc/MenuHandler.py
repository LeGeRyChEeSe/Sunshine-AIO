import json
import sys
from typing import List, Dict
from misc.Config import DownloadManager
from misc.SystemRequests import SystemRequests
from misc.Uninstaller import SunshineAIOUninstaller
from . import __version__


class MenuHandler:
    """
        The Menu Handler.

        Attribtues
        ----------
        page: :class:`int`
            The current page.
        choices: :class:`JSON`
            The list of all choices.
        user_input: :class:`int`
            The user input.
    """

    def __init__(self, base_path: str) -> None:
        self._page: int = 0
        self._choices: List[Dict[str, str]]
        self._choices_number: int
        self._sr: SystemRequests = SystemRequests(base_path)
        self._logo_menu_path: str = f"{self._sr._base_path}\\misc\\ressources\\logo_menu.txt"
        self._menu_choices_path: str = f"{self._sr._base_path}\\misc\\variables\\menu_choices.json"
        self._user_input: int
        self._rerun_as_admin = self._sr.rerun_as_admin
        self._dm: DownloadManager = DownloadManager(self._sr, self._page)
        self._config = self._dm.config
        self._uninstaller: SunshineAIOUninstaller = SunshineAIOUninstaller(self._sr)
        self._map = [
            {
                "1": self._dm.download_all,
                "2": lambda: self._dm.download_sunshine(selective=True),
                "3": lambda: self._dm.download_vdd(selective=True),
                "4": lambda: self._dm.download_svm(selective=True),
                "5": lambda: self._dm.download_playnite(selective=True),
                "6": lambda: self._dm.download_playnite_watcher(selective=True),
                "7": self._next_page,
                "8": self._show_uninstall_menu,
                "0": sys.exit
            },
            {
                "1": lambda: self._dm.download_all(install=False),
                "2": self._next_page,
                "3": lambda: self._config.configure_sunshine(selective=True),
                "4": lambda: self._sr.install_windows_display_manager(selective=True),
                "5": self._config.open_sunshine_settings,
                "6": self._config.open_playnite,
                "7": self._previous_page,
                "0": sys.exit
            },
            {
                "1": lambda: self._dm.download_sunshine(install=False, selective=True),
                "2": lambda: self._dm.download_vdd(install=False, selective=True),
                "3": lambda: self._dm.download_svm(install=False, selective=True),
                "4": lambda: self._dm.download_mmt(selective=True),
                "5": lambda: self._dm.download_vsync_toggle(selective=True),
                "6": lambda: self._dm.download_playnite(install=False, selective=True),
                "7": lambda: self._dm.download_playnite_watcher(install=False, selective=True),
                "8": self._previous_page,
                "0": sys.exit
            },
            {
                "1": self._show_uninstall_report,
                "2": self._show_installed_components,
                "3": self._uninstall_specific_component,
                "4": self._uninstall_all_components,
                "5": self._previous_page,
                "0": sys.exit
            }
        ]

        self._set_choices()

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self):
        raise ValueError("No manual edit allowed.")

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self):
        raise ValueError("No manual edit allowed.")

    @property
    def choices_number(self):
        return self._choices_number

    @choices_number.setter
    def choices_number(self):
        raise ValueError("No manual edit allowed.")

    @property
    def logo_menu_path(self):
        return self._logo_menu_path

    @logo_menu_path.setter
    def logo_menu_path(self):
        raise ValueError("No manual edit allowed.")

    @property
    def menu_choices_path(self):
        return self._menu_choices_path

    @menu_choices_path.setter
    def menu_choices_path(self):
        raise ValueError("No manual edit allowed.")

    @property
    def user_input(self):
        return self._user_input

    @user_input.setter
    def user_input(self):
        raise ValueError("No manual edit allowed.")

    @property
    def sr(self):
        return self._sr

    @sr.setter
    def sr(self):
        raise ValueError("No manual edit allowed.")

    @property
    def rerun_as_admin(self):
        return self._rerun_as_admin

    @rerun_as_admin.setter
    def rerun_as_admin(self):
        raise ValueError("No manual edit allowed.")

    @property
    def dm(self):
        return self._dm

    @dm.setter
    def dm(self):
        raise ValueError("No manual edit allowed.")

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self):
        raise ValueError("No manual edit allowed.")

    @property
    def map(self):
        return self._map

    @map.setter
    def map(self):
        raise ValueError("No manual edit allowed.")

    def _print_logo(self) -> None:
        with open(self._logo_menu_path, 'r') as logo_file:
            lines = logo_file.readlines()

        for line in lines:
            print(line.rstrip())

    def _print_version(self) -> None:
        print(f"{__version__}\n")

    def _set_choices(self) -> None:
        with open(self._menu_choices_path, 'rb') as choices:
            self._choices = json.loads(choices.read())
        self._set_choices_number()

    def _set_choices_number(self) -> None:
        self._choices_number = len(self._choices[self._page]) - 1

    def _print_page(self) -> None:
        print("\nMenu:")
        for choice_number, choice in self._choices[self._page].items():
            print(f"{choice_number}. {choice}")

    def _get_user_input(self) -> bool:
        try:
            user_input = int(input(f"\nPlease choose an option (0-{self._choices_number}): "))
            if 0 <= user_input <= self._choices_number:
                self._user_input = user_input
                return True
        except ValueError:
            return False
        else:
            return False

    def _next_page(self):
        self._page += 1
        self._set_choices_number()

    def _previous_page(self):
        self._page -= 1
        self._set_choices_number()

    def _get_selection(self):
        return self._map[self._page][str(self._user_input)]

    def _execute_selection(self):
        # Execute the method associated with the user_input
        self._get_selection()()

    def _show_uninstall_menu(self):
        """Affiche le menu de désinstallation."""
        self._page = 3  # Page de désinstallation
        self._set_choices_number()

    def _show_uninstall_report(self):
        """Affiche le rapport de désinstallation."""
        self._sr.clear_screen()
        print(self._uninstaller.generate_uninstall_report())
        input("\nAppuyez sur Entrée pour continuer...")

    def _show_installed_components(self):
        """Affiche les composants installés."""
        self._sr.clear_screen()
        installed = self._uninstaller.list_installed_components()
        
        if installed:
            print("Composants Sunshine-AIO installés:")
            for component in installed:
                print(f"  ✓ {component}")
        else:
            print("Aucun composant Sunshine-AIO détecté sur ce système.")
        
        input("\nAppuyez sur Entrée pour continuer...")

    def _uninstall_specific_component(self):
        """Désinstalle un composant spécifique."""
        self._sr.clear_screen()
        print("Composants disponibles pour désinstallation:")
        
        components_list = list(self._uninstaller.components.values())
        for i, component in enumerate(components_list, 1):
            print(f"  {i}. {component['name']}")
        
        try:
            choice = int(input(f"\nChoisissez un composant (1-{len(components_list)}): ")) - 1
            if 0 <= choice < len(components_list):
                component_name = components_list[choice]['name']
                print(f"\nDésinstallation de {component_name}...")
                
                if self._uninstaller.uninstall_component(component_name):
                    print(f"✓ {component_name} désinstallé avec succès!")
                else:
                    print(f"❌ Problème lors de la désinstallation de {component_name}")
            else:
                print("Sélection invalide.")
        except ValueError:
            print("Entrée invalide.")
        
        input("\nAppuyez sur Entrée pour continuer...")

    def _uninstall_all_components(self):
        """Désinstalle tous les composants."""
        self._sr.clear_screen()
        print("ATTENTION: Cette opération va supprimer TOUS les composants Sunshine-AIO!")
        print("Cette action est irréversible.")
        
        if self._uninstaller.uninstall_all():
            print("\n✓ Désinstallation complète terminée avec succès!")
        else:
            print("\n❌ Désinstallation terminée avec des avertissements.")
            print("Consultez les messages ci-dessus pour plus de détails.")
        
        input("\nAppuyez sur Entrée pour continuer...")

    def print_menu(self):
        while True:
            self._sr.clear_screen()
            self._print_logo()
            self._print_version()
            self._print_page()
            if self._get_user_input():
                self._execute_selection()
