from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (QIcon, QValidator, QRegularExpressionValidator, QShowEvent, QKeyEvent, QCloseEvent,
                           QTextOption)
from PySide6.QtWidgets import (QApplication, QWidget, QStackedLayout, QFormLayout, QHBoxLayout, QLineEdit, QRadioButton,
                               QButtonGroup, QPushButton, QLabel, QComboBox, QFileDialog, QSpacerItem, QSizePolicy,
                               QMessageBox)
from paramiko import SSHClient, MissingHostKeyPolicy, Channel
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

from widget import Heading, ReadOnlyTextEdit, HLine
from worker import SSHConnectWorker, SSHReadStdIOWorker


class Window(QWidget):
    closed = Signal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowIcon(QIcon("images/logo.ico"))

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)

        rectangle = self.frameGeometry()
        rectangle.moveCenter(self.screen().availableGeometry().center())
        self.move(rectangle.topLeft())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()

        super().closeEvent(event)


# noinspection PyAttributeOutsideInit
class SSHClientWindow(Window):
    # noinspection PyAttributeOutsideInit
    class ConnectPage(QWidget):
        def __init__(self, parent: "SSHClientWindow") -> None:
            super().__init__()

            self.parent = parent

            self.init_widgets()
            self.init_workers()

        def init_widgets(self) -> None:
            self.input_host = QLineEdit()
            self.input_host.setValidator(QRegularExpressionValidator(r"^\S+$"))

            self.input_username = QLineEdit()
            self.input_username.setValidator(QRegularExpressionValidator(r"^\S+$"))

            self.button_password = QRadioButton("Password")
            self.button_password.setChecked(True)
            self.button_password.toggled.connect(self.group_auth_clicked)

            self.input_password = QLineEdit()

            area_password = QHBoxLayout()
            area_password.addWidget(self.button_password)
            area_password.addWidget(self.input_password)

            widget_password = QWidget()
            widget_password.setLayout(area_password)

            self.button_key = QRadioButton("Key")
            self.button_key.setMinimumWidth(self.button_password.sizeHint().width())
            self.button_key.toggled.connect(self.group_auth_clicked)

            self.input_key = QLineEdit()
            self.input_key.setDisabled(True)

            self.button_choose_key = QPushButton("Choose")
            self.button_choose_key.clicked.connect(self.button_choose_key_clicked)
            self.button_choose_key.setDisabled(True)

            area_key = QHBoxLayout()
            area_key.addWidget(self.button_key)
            area_key.addWidget(self.input_key)
            area_key.addWidget(self.button_choose_key)

            widget_key = QWidget()
            widget_key.setLayout(area_key)

            self.group_auth = QButtonGroup()
            self.group_auth.addButton(self.button_password)
            self.group_auth.addButton(self.button_key)

            button_connect = QPushButton("Connect")
            button_connect.clicked.connect(self.button_connect_clicked)

            layout = QFormLayout()
            layout.addRow(Heading("General", 6, "bold"))
            layout.addItem(QSpacerItem(0, 6))
            layout.addRow("Host", self.input_host)
            layout.addRow("Username", self.input_username)
            layout.addItem(QSpacerItem(0, 6))
            layout.addRow(Heading("Authentication", 6, "bold"))
            layout.addItem(QSpacerItem(0, 6))
            layout.addRow(widget_password)
            layout.addRow(widget_key)
            layout.addItem(QSpacerItem(0, 10, QSizePolicy.Expanding, QSizePolicy.MinimumExpanding))
            layout.addRow(button_connect)

            self.setLayout(layout)

        def init_workers(self) -> None:
            self.worker_connect = SSHConnectWorker(self.parent.ssh_client)
            self.worker_connect.completed.connect(self.ssh_client_connected)
            self.worker_connect.failed.connect(self.handle_worker_exception)

        def handle_worker_exception(self, e: Exception) -> None:
            QMessageBox.critical(
                self.parent,
                "Error Occurred",
                str(e)
            )

            self.setEnabled(True)

        def group_auth_clicked(self) -> None:
            if self.button_password.isChecked():
                self.input_password.setEnabled(True)
            else:
                self.input_password.setDisabled(True)

            if self.button_key.isChecked():
                self.input_key.setEnabled(True)
                self.button_choose_key.setEnabled(True)
            else:
                self.input_key.setDisabled(True)
                self.button_choose_key.setDisabled(True)

        def button_choose_key_clicked(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self.parent,
                caption="Choose Key",
                filter="All Files (*)"
            )

            if path:
                self.input_key.setText(path)

        def button_connect_clicked(self) -> None:
            state, _, _ = self.input_host.validator().validate(self.input_host.text(), 0)

            if state != QValidator.State.Acceptable:
                return QMessageBox.warning(
                    self.parent,
                    "Host Invalid",
                    "Host can not be empty."
                )

            state, _, _ = self.input_username.validator().validate(self.input_username.text(), 0)

            if state != QValidator.State.Acceptable:
                return QMessageBox.warning(
                    self.parent,
                    "Username Invalid",
                    "Username can not be empty."
                )

            self.setDisabled(True)

            self.worker_connect.set_args({
                "hostname": self.input_host.text(),
                "username": self.input_username.text(),
                "password": self.input_password.text() if self.button_password.isChecked() else None,
                "key_filename": self.input_key.text() if self.button_key.isChecked() else None,
                "timeout": 5,
                "banner_timeout": 5,
                "auth_timeout": 5,
                "channel_timeout": 5
            })
            self.worker_connect.start()

        def ssh_client_connected(self) -> None:
            self.parent.page_command.update_workers()
            self.parent.stack.setCurrentWidget(self.parent.page_command)

    # noinspection PyAttributeOutsideInit
    class CommandPage(QWidget):
        class CommandLineEdit(QLineEdit):
            def keyPressEvent(self, event: QKeyEvent) -> None:
                if event.key() == Qt.Key_Up:
                    self.undo()
                elif event.key() == Qt.Key_Down:
                    self.redo()
                else:
                    super().keyPressEvent(event)

        def __init__(self, parent: "SSHClientWindow") -> None:
            super().__init__()

            self.parent = parent
            self.channel: Channel | None = None

            self.init_widgets()
            self.init_workers()

        def init_widgets(self) -> None:
            self.input_command = SSHClientWindow.CommandPage.CommandLineEdit()
            self.input_command.setProperty("font-family", "Cascadia Code")
            self.input_command.returnPressed.connect(self.button_execute_clicked)

            button_execute = QPushButton("Execute")
            button_execute.clicked.connect(self.button_execute_clicked)

            area_command = QHBoxLayout()
            area_command.addWidget(self.input_command)
            area_command.addWidget(button_execute)

            self.input_terminal = ReadOnlyTextEdit()
            self.input_terminal.setProperty("font-family", "Cascadia Code")

            layout = QFormLayout()
            layout.addRow("Command", area_command)
            layout.addRow("Terminal", self.input_terminal)

            self.setLayout(layout)

        def init_workers(self) -> None:
            self.worker_read_stdout = SSHReadStdIOWorker()
            self.worker_read_stdout.received.connect(self.ssh_client_stdout_received)
            self.worker_read_stdout.completed.connect(self.ssh_client_session_closed)
            self.worker_read_stdout.failed.connect(self.handle_worker_exception)

        def update_workers(self) -> None:
            self.channel = self.parent.ssh_client.invoke_shell()
            self.worker_read_stdout.stdio = self.channel.makefile()
            self.worker_read_stdout.start()

        def handle_worker_exception(self, e: Exception) -> None:
            QMessageBox.critical(
                self.parent,
                "Error Occurred",
                str(e)
            )

            self.parent.close()

        def ssh_client_stdout_received(self, line: str) -> None:
            self.input_terminal.append(line)

        def ssh_client_session_closed(self) -> None:
            if self.parent.isActiveWindow():
                QMessageBox.warning(
                    self.parent,
                    "Session Closed",
                    "The SSH session has been closed."
                )

                self.parent.close()

        def button_execute_clicked(self) -> None:
            command = self.input_command.text() + "\n"
            self.input_command.clear()
            self.channel.send(command.encode())

        def showEvent(self, _) -> None:
            if self.parent.height() < 600:
                self.parent.resize(self.parent.width(), 600)

            self.input_command.setFocus()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.ssh_client = SSHClient()
        self.ssh_client.set_missing_host_key_policy(MissingHostKeyPolicy())

        self.setWindowTitle("SSH Client")
        self.resize(800, 1)

        self.init_widgets()

    def init_widgets(self) -> None:
        self.page_connect = SSHClientWindow.ConnectPage(self)
        self.page_command = SSHClientWindow.CommandPage(self)

        self.stack = QStackedLayout()
        self.stack.addWidget(self.page_connect)
        self.stack.addWidget(self.page_command)

        self.setLayout(self.stack)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)

        self.setFocus()
        self.page_connect.input_host.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.ssh_client.close()

        super().closeEvent(event)


# noinspection PyAttributeOutsideInit
class SSHKeygenWindow(Window):
    ALGORITHMS = [
        ("Ed25519", "ed25519"),
        ("RSA", "rsa")
    ]

    KEY_SIZES = [
        4096,
        3072,
        2048
    ]

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("SSH Key Pair Generator")
        self.resize(600, 600)

        self.init_widgets()
        self.update_widgets()

    def init_widgets(self) -> None:
        self.select_algorithm = QComboBox()
        self.select_algorithm.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.select_algorithm.currentIndexChanged.connect(self.select_algorithm_item_changed)

        layout_algorithm = QHBoxLayout()
        layout_algorithm.addWidget(QLabel("Algorithm"))
        layout_algorithm.addWidget(self.select_algorithm)

        self.select_key_size = QComboBox()
        self.select_key_size.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.select_key_size.setDisabled(True)

        layout_key_size = QHBoxLayout()
        layout_key_size.addWidget(QLabel("Key Size"))
        layout_key_size.addWidget(self.select_key_size)

        button_generate = QPushButton("Generate")
        button_generate.clicked.connect(self.button_generated_clicked)

        layout_generate = QHBoxLayout()
        layout_generate.addLayout(layout_algorithm)
        layout_generate.addItem(QSpacerItem(10, 0))
        layout_generate.addLayout(layout_key_size)
        layout_generate.addItem(QSpacerItem(10, 0))
        layout_generate.addWidget(button_generate)

        self.input_private_key = ReadOnlyTextEdit()
        self.input_private_key.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)

        self.input_public_key = ReadOnlyTextEdit()
        self.input_public_key.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)

        button_export_private_key = QPushButton("Export Private Key")
        button_export_private_key.clicked.connect(self.button_export_private_key_clicked)

        button_copy_public_key = QPushButton("Copy Public Key")
        button_copy_public_key.clicked.connect(self.button_copy_public_key_clicked)

        layout_export = QHBoxLayout()
        layout_export.addWidget(button_export_private_key)
        layout_generate.addItem(QSpacerItem(10, 0))
        layout_export.addWidget(button_copy_public_key)

        layout = QFormLayout()
        layout.addRow(layout_generate)
        layout.addItem(QSpacerItem(0, 10))
        layout.addRow(HLine())
        layout.addItem(QSpacerItem(0, 10))
        layout.addRow("Private Key", self.input_private_key)
        layout.addRow("Public Key", self.input_public_key)
        layout.addItem(QSpacerItem(0, 10))
        layout.addRow(layout_export)

        self.setLayout(layout)

    def update_widgets(self) -> None:
        for algorithm, algorithm_id in SSHKeygenWindow.ALGORITHMS:
            self.select_algorithm.addItem(algorithm, algorithm_id)

        for key_size in SSHKeygenWindow.KEY_SIZES:
            self.select_key_size.addItem(str(key_size), key_size)

    def select_algorithm_item_changed(self) -> None:
        if self.select_algorithm.currentData() == "rsa":
            self.select_key_size.setEnabled(True)
        else:
            self.select_key_size.setDisabled(True)

    def button_generated_clicked(self) -> None:
        self.input_private_key.clear()
        self.input_public_key.clear()

        if self.select_algorithm.currentData() == "ed25519":
            private_key = ed25519.Ed25519PrivateKey.generate()
        elif self.select_algorithm.currentData() == "rsa":
            private_key = rsa.generate_private_key(65537, self.select_key_size.currentData())
        else:
            return

        public_key = private_key.public_key()

        self.input_private_key.setText(
            private_key.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption()).decode()
        )
        self.input_public_key.setText(
            public_key.public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH).decode()
        )

    def button_export_private_key_clicked(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Export Private Key",
            dir="id_" + self.select_algorithm.currentData(),
            filter="All Files (*)"
        )

        if not path:
            return

        with open(path, "w") as f:
            f.write(self.input_private_key.toPlainText())

    def button_copy_public_key_clicked(self) -> None:
        QApplication.clipboard().setText(self.input_public_key.toPlainText())
