import sys
import ctypes

from PySide6.QtGui import QIcon, QFontDatabase
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedLayout, QWidget
from qt_material import apply_stylesheet

from widget import PageStack


# noinspection PyAttributeOutsideInit
class MainWindow(QMainWindow):
    def __init__(self, app: QApplication) -> None:
        super().__init__()

        self.app = app
        self.project_id: str | None = None

        self.set_theme("dark_blue.xml")
        self.setWindowIcon(QIcon("images/logo.png"))
        self.setWindowTitle("Google Cloud GUI")
        self.resize(1280, 720)

        self.init_menu()
        self.init_widgets()

        self.statusBar().showMessage("Google Cloud GUI")

    def init_menu(self) -> None:
        from menu import MenuBar

        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

    def init_widgets(self) -> None:
        from page import LoadingPage, ConnectPage, InstancePage

        self.page_loading = LoadingPage()
        self.page_loading.hide()

        self.page_connect = ConnectPage(self)
        self.page_instance = InstancePage(self)

        self.stack = PageStack()
        self.stack.addWidget(self.page_connect)
        self.stack.addWidget(self.page_instance)

        layout = QStackedLayout()
        layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        layout.addWidget(self.stack)
        layout.addWidget(self.page_loading)

        widget = QWidget()
        widget.setLayout(layout)

        self.setCentralWidget(widget)

    def set_theme(self, theme: str) -> None:
        apply_stylesheet(self.app, theme=theme, css_file="assets/style.css")


def main() -> None:
    app = QApplication(sys.argv)
    QFontDatabase.addApplicationFont("assets/cascadia-code.ttf")
    main_window = MainWindow(app)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("google-cloud-gui")
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
