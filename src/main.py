import os
from misc.MenuHandler import MenuHandler

if __name__ == "__main__":
    menu = MenuHandler(os.path.dirname(__file__))
    menu.rerun_as_admin()
    menu.print_menu()
