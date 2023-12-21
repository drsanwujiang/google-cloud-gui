from PySide6.QtWidgets import QMenuBar, QMenu

from main import MainWindow
from window import SSHClientWindow, SSHKeygenWindow


# noinspection PyAttributeOutsideInit
class MenuBar(QMenuBar):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__()

        self.parent = parent

        self.init_menu()

    def init_menu(self) -> None:
        menu_theme = QMenu("Theme")
        menu_theme.addAction("Dark Amber", lambda: self.parent.set_theme("dark_amber.xml"))
        menu_theme.addAction("Dark Blue", lambda: self.parent.set_theme("dark_blue.xml"))
        menu_theme.addAction("Dark Cyan", lambda: self.parent.set_theme("dark_cyan.xml"))
        menu_theme.addAction("Dark Lightgreen", lambda: self.parent.set_theme("dark_lightgreen.xml"))
        menu_theme.addAction("Dark Pink", lambda: self.parent.set_theme("dark_pink.xml"))
        menu_theme.addAction("Dark Purple", lambda: self.parent.set_theme("dark_purple.xml"))
        menu_theme.addAction("Dark Red", lambda: self.parent.set_theme("dark_red.xml"))
        menu_theme.addAction("Dark Teal", lambda: self.parent.set_theme("dark_teal.xml"))
        menu_theme.addAction("Dark Yellow", lambda: self.parent.set_theme("dark_yellow.xml"))

        menu_appearance = QMenu("Appearance")
        menu_appearance.addMenu(menu_theme)

        menu_tools = QMenu("Tools")
        menu_tools.addAction("SSH", self.show_ssh_client_window)
        menu_tools.addAction("SSH Keygen", self.show_ssh_keygen_window)

        self.addMenu(menu_appearance)
        self.addMenu(menu_tools)

    def show_ssh_client_window(self) -> None:
        if hasattr(self, "window_ssh") and getattr(self, "window_ssh") is not None:
            return

        self.window_ssh = SSHClientWindow()
        self.window_ssh.closed.connect(lambda: setattr(self, "window_ssh", None))
        self.window_ssh.show()

    def show_ssh_keygen_window(self) -> None:
        if not hasattr(self, "window_ssh_keygen") or getattr(self, "window_ssh_keygen") is None:
            self.window_ssh_keygen = SSHKeygenWindow()
            self.window_ssh_keygen.closed.connect(lambda: setattr(self, "window_ssh_keygen", None))

        self.window_ssh_keygen.show()
