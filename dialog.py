from PySide6.QtGui import QIcon, QValidator, QRegularExpressionValidator, QIntValidator, QTextOption
from PySide6.QtWidgets import (QDialog, QWidget, QFormLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton, QSpacerItem,
                               QCheckBox, QTextEdit, QMessageBox, QSizePolicy)
from google.cloud.compute_v1 import Tags, Metadata, Items

from widget import Heading


class Dialog(QDialog):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowIcon(QIcon("images/logo.ico"))


# noinspection PyAttributeOutsideInit
class CreateInstanceDialog(Dialog):
    INSTANCE_MACHINE_TYPES = [
        ("E2 Micro (2 vCPU, 1 core, 1 GB memory)", "e2-micro"),
        ("E2 Small (2 vCPU, 1 core, 2 GB memory)", "e2-small"),
        ("E2 Medium (2 vCPU, 2 core, 4 GB memory)", "e2-medium")
    ]

    INSTANCE_NETWORK_TIERS = [
        ("Standard", "STANDARD"),
        ("Premium", "PREMIUM")
    ]

    INSTANCE_IMAGES = [
        ("Debian 12", "projects/debian-cloud/global/images/family/debian-12"),
        ("Debian 11", "projects/debian-cloud/global/images/family/debian-11"),
        ("Debian 10", "projects/debian-cloud/global/images/family/debian-10"),
    ]

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Create Instance")
        self.resize(800, 1)

        self.init_widgets()
        self.update_widgets()

    def init_widgets(self) -> None:
        self.input_instance_name = QLineEdit()
        self.input_instance_name.setValidator(QRegularExpressionValidator(r"^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$"))

        self.input_instance_description = QLineEdit()

        self.input_instance_hostname = QLineEdit()
        self.input_instance_hostname.setValidator(QRegularExpressionValidator(
            r"^[a-z]([-a-z0-9]{0,61}[a-z0-9])?(\.[a-z]([-a-z0-9]{0,61}[a-z0-9])?)+$")
        )

        self.input_instance_machine_type = QComboBox()
        self.input_instance_network_tier = QComboBox()

        self.input_instance_disk_size = QLineEdit("10")
        self.input_instance_disk_size.setValidator(QIntValidator(1, 65536))

        self.input_instance_image = QComboBox()

        button_create = QPushButton("Create")
        button_create.clicked.connect(self.button_create_clicked)

        layout = QFormLayout()
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow(Heading("Basic Information", 6, "bold"))
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow("Name", self.input_instance_name)
        layout.addRow("Description", self.input_instance_description)
        layout.addRow("Hostname", self.input_instance_hostname)
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow(Heading("Machine Configuration", 6, "bold"))
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow("Machine Type", self.input_instance_machine_type)
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow(Heading("Network Interface", 6, "bold"))
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow("Network Tier", self.input_instance_network_tier)
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow(Heading("Storage", 6, "bold"))
        layout.addItem(QSpacerItem(0, 6))
        layout.addRow("Disk Size (GB)", self.input_instance_disk_size)
        layout.addRow("Image", self.input_instance_image)
        layout.addItem(QSpacerItem(0, 10, QSizePolicy.Expanding, QSizePolicy.MinimumExpanding))
        layout.addRow(button_create)

        self.setLayout(layout)

    def update_widgets(self) -> None:
        for machine_type, machine_type_id in self.INSTANCE_MACHINE_TYPES:
            self.input_instance_machine_type.addItem(machine_type, machine_type_id)

        self.input_instance_machine_type.setCurrentIndex(1)

        for network_tier, network_tier_id in self.INSTANCE_NETWORK_TIERS:
            self.input_instance_network_tier.addItem(network_tier, network_tier_id)

        self.input_instance_network_tier.setCurrentIndex(1)

        for image, image_id in self.INSTANCE_IMAGES:
            self.input_instance_image.addItem(image, image_id)

        self.input_instance_image.setCurrentIndex(1)

    def button_create_clicked(self) -> None:
        state, _, _ = self.input_instance_name.validator().validate(self.input_instance_name.text(), 0)

        if state != QValidator.State.Acceptable:
            return QMessageBox.warning(
                self,
                "Instance Name Invalid",
                "Instance name must start with a lowercase letter followed by up to 62 lowercase letters, numbers, or "
                "hyphens, and cannot end with a hyphen."
            )

        state, _, _ = self.input_instance_hostname.validator().validate(self.input_instance_hostname.text(), 0)

        if self.input_instance_hostname.text() and state != QValidator.State.Acceptable:
            return QMessageBox.warning(
                self,
                "Hostname Invalid",
                """Hostname must follow these rules:

 · Use at least 2 labels for your hostname
 · Separate labels with dots
 · Start your labels with a letter (a-z)
 · End them with a letter or a digit (0-9)
 · Have letters, digits, or a hyphen (-) in between
 · Keep it short (from 4 to 253 characters)""")

        self.instance_info = {
            "name": self.input_instance_name.text(),
            "description": self.input_instance_description.text(),
            "hostname": self.input_instance_hostname.text() if self.input_instance_hostname.text() else None,
            "machine_type": self.input_instance_machine_type.currentData(),
            "network_tier": self.input_instance_network_tier.currentData(),
            "disk_size": int(self.input_instance_disk_size.text()),
            "image": self.input_instance_image.currentData()
        }

        self.accept()


# noinspection PyAttributeOutsideInit
class SetInstanceTagsDialog(Dialog):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.tags: Tags | None = None

        self.setWindowTitle("Set Tags")
        self.resize(400, 1)

        self.init_widgets()

    def init_widgets(self) -> None:
        self.check_http_server = QCheckBox("HTTP Server")
        self.check_https_server = QCheckBox("HTTPS Server")

        button_set = QPushButton("Set")
        button_set.clicked.connect(self.button_set_clicked)

        layout = QFormLayout()
        layout.addRow(self.check_http_server)
        layout.addRow(self.check_https_server)
        layout.addItem(QSpacerItem(0, 10, QSizePolicy.Expanding, QSizePolicy.MinimumExpanding))
        layout.addRow(button_set)

        self.setLayout(layout)

    def update_widgets(self) -> None:
        if self.tags:
            self.check_http_server.setChecked("http-server" in self.tags.items)
            self.check_https_server.setChecked("https-server" in self.tags.items)

    def button_set_clicked(self) -> None:
        # Remove http-server and https-server tags
        if "http-server" in self.tags.items:
            self.tags.items.remove("http-server")

        if "https-server" in self.tags.items:
            self.tags.items.remove("https-server")

        # Add http-server or https-server tags
        if self.check_http_server.isChecked():
            self.tags.items.append("http-server")

        if self.check_https_server.isChecked():
            self.tags.items.append("https-server")

        self.accept()


# noinspection PyAttributeOutsideInit
class SetInstanceMetadataDialog(Dialog):
    # noinspection PyAttributeOutsideInit
    class AddKeyDialog(Dialog):
        def __init__(self, parent: QWidget = None) -> None:
            super().__init__(parent)

            self.setWindowTitle("Add Key")
            self.resize(400, 1)

            self.init_widgets()

        def init_widgets(self) -> None:
            self.input_key = QLineEdit()
            self.input_key.setValidator(QRegularExpressionValidator(r"^[a-zA-Z0-9_-]+$"))

            button_add = QPushButton("Add")
            button_add.clicked.connect(self.button_add_clicked)

            layout = QFormLayout()
            layout.addRow("Key", self.input_key)
            layout.addItem(QSpacerItem(0, 10))
            layout.addRow(button_add)

            self.setLayout(layout)

        def button_add_clicked(self) -> None:
            state, _, _ = self.input_key.validator().validate(self.input_key.text(), 0)

            if state != QValidator.State.Acceptable:
                return QMessageBox.warning(
                    self,
                    "Key Invalid",
                    "Key cannot contain special characters or blank spaces. Only letters, numbers, underscores(_) and "
                    "hyphens(-) are allowed."
                )

            self.accept()

    def __init__(self) -> None:
        super().__init__()

        self.metadata: Metadata | None = None
        self.metadata_items = {}

        self.setWindowTitle("Set Metadata")
        self.resize(600, 1)

        self.init_widgets()

    def init_widgets(self) -> None:
        self.select_key = QComboBox()
        self.select_key.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.select_key.currentIndexChanged.connect(self.select_key_item_changed)

        self.button_add_key = QPushButton("Add")
        self.button_add_key.clicked.connect(self.button_add_key_clicked)

        area_key = QHBoxLayout()
        area_key.addWidget(self.select_key)
        area_key.addWidget(self.button_add_key)

        self.input_value = QTextEdit()
        self.input_value.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)

        button_set = QPushButton("Set")
        button_set.clicked.connect(self.button_set_clicked)

        layout = QFormLayout()
        layout.addRow("Key", area_key)
        layout.addRow("Value", self.input_value)
        layout.addItem(QSpacerItem(0, 10))
        layout.addRow(button_set)

        self.setLayout(layout)

    def update_widgets(self) -> None:
        for item in self.metadata.items:
            self.metadata_items[item.key] = item.value
            self.select_key.addItem(item.key)

    def select_key_item_changed(self) -> None:
        if (key := self.select_key.currentText()) in self.metadata_items:
            self.input_value.setText(self.metadata_items[key])
        else:
            self.input_value.setText("")

    def button_add_key_clicked(self) -> None:
        dialog = SetInstanceMetadataDialog.AddKeyDialog()

        if not dialog.exec():
            return

        if (key := dialog.input_key.text()) not in self.metadata_items:
            self.metadata_items[key] = ""
            self.select_key.addItem(key)

        self.select_key.setCurrentText(key)

    def button_set_clicked(self) -> None:
        key = self.select_key.currentText()
        value = self.input_value.toPlainText()

        if key:
            self.metadata_items[key] = value

        self.metadata.items = [Items(key=key, value=value) for key, value in self.metadata_items.items()]
        self.accept()
