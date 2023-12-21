import os
import json
import datetime
from copy import deepcopy
from typing import Iterable

from PySide6.QtCore import Qt, QPropertyAnimation, QPoint
from PySide6.QtGui import QPixmap, QColor, QPaintEvent
from PySide6.QtWidgets import (QWidget, QLayout, QHBoxLayout, QVBoxLayout, QMenu, QLabel, QPushButton, QFileDialog,
                               QMessageBox, QListWidget, QLineEdit, QComboBox, QSizePolicy, QFormLayout, QScrollArea,
                               QSpacerItem, QGraphicsOpacityEffect)
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import GoogleAuthError
from google.cloud.compute_v1 import Instance

from main import MainWindow
from widget import Spinner, HLine, VLine, Heading, ReadOnlyLineEdit
from dialog import CreateInstanceDialog, SetInstanceTagsDialog, SetInstanceMetadataDialog
from worker import (LoadInstanceListWorker, LoadInstanceDetailsWorker, CreateInstanceWorker, StartInstanceWorker,
                    ResumeInstanceWorker, StopInstanceWorker, SuspendInstanceWorker, ResetInstanceWorker,
                    DeleteInstanceWorker, SetInstanceTagsWorker, SetInstanceMetadataWorker)
from cloud import GoogleCloudClient


class LoadingPage(QWidget):
    class LoadingLabel(Heading):
        def __init__(self) -> None:
            super().__init__("Loading...", 4)

            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        def center(self) -> None:
            self.move(int(self.parentWidget().width() / 2 - self.width() / 2),
                      int(self.parentWidget().height() / 2 + 50))

        def paintEvent(self, event: QPaintEvent) -> None:
            super().paintEvent(event)

            self.center()

    def __init__(self) -> None:
        super().__init__()

        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("background: rgba(0, 0, 0, 0.5);")

        self.effect_opacity = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.effect_opacity)

        self.animation_opacity = QPropertyAnimation()
        self.animation_opacity.setTargetObject(self.effect_opacity)
        self.animation_opacity.setPropertyName(b"opacity")

        spinner = Spinner()
        spinner.set_color(QColor(147, 219, 233, 255))
        spinner.start()

        self.label_message = LoadingPage.LoadingLabel()

        layout = QVBoxLayout()
        layout.addWidget(spinner)
        layout.addWidget(self.label_message)

        self.setLayout(layout)

    def set_loading_message(self, message: str) -> None:
        self.label_message.setText(message)

    def fade_in(self, milliseconds: int = 300) -> None:
        if not self.isVisible():
            self.show()

        self.animation_opacity.setDuration(milliseconds)
        self.animation_opacity.setStartValue(self.effect_opacity.opacity())
        self.animation_opacity.setEndValue(1.0)
        self.animation_opacity.start()

    def fade_out(self, milliseconds: int = 300) -> None:
        if self.effect_opacity.opacity() > 0.0:
            self.animation_opacity.setDuration(milliseconds)
            self.animation_opacity.setStartValue(self.effect_opacity.opacity())
            self.animation_opacity.setEndValue(0.0)
            self.animation_opacity.start()

        self.animation_opacity.finished.connect(self.fade_out_finished)

    def fade_out_finished(self) -> None:
        self.animation_opacity.finished.disconnect(self.fade_out_finished)

        if self.isVisible():
            self.hide()


# noinspection PyAttributeOutsideInit
class ConnectPage(QWidget):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__()

        self.parent = parent
        self.google_cloud_client = GoogleCloudClient.default_client

        self.init_widgets()

    def init_widgets(self) -> None:
        background_image = QLabel()
        background_image.setPixmap(QPixmap("images/google-cloud.png"))
        background_image.setAlignment(Qt.AlignCenter)

        button_connect = QPushButton("Connect to Google Cloud")
        button_connect.clicked.connect(self.button_connect_clicked)

        layout = QVBoxLayout()
        layout.addWidget(background_image)
        layout.addWidget(button_connect)

        self.setLayout(layout)

    def button_connect_clicked(self, *, filename: str = None) -> None:
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(
                None,
                caption="Choose Credentials",
                filter="JSON File (*.json)"
            )

        if not os.path.exists(filename):
            return

        try:
            with open(filename, "r") as f:
                credentials = json.load(f)

            self.google_cloud_client.load_credentials(credentials=credentials)
            self.parent.project_id = credentials["project_id"]
            self.parent.stack.setCurrentWidget(self.parent.page_instance)
            self.parent.page_instance.update_widgets()
        except (OSError, json.JSONDecodeError, GoogleAuthError):
            QMessageBox.critical(
                self,
                "Credentials Invalid",
                "Google Cloud service account credentials format invalid."
            )

            self.parent.statusBar().showMessage(
                "Error occurred: Google Cloud service account credentials format invalid."
            )


# noinspection PyAttributeOutsideInit
class InstancePage(QWidget):
    ZONES = [
        ("Taiwan (asia-east1-a)", "asia-east1-a"),
        ("Taiwan (asia-east1-b)", "asia-east1-b"),
        ("Taiwan (asia-east1-c)", "asia-east1-c"),
        ("Hong Kong (asia-east2-a)", "asia-east2-a"),
        ("Hong Kong (asia-east2-b)", "asia-east2-b"),
        ("Hong Kong (asia-east2-c)", "asia-east2-c"),
        ("Tokyo (asia-northeast1-a)", "asia-northeast1-a"),
        ("Tokyo (asia-northeast1-b)", "asia-northeast1-b"),
        ("Tokyo (asia-northeast1-c)", "asia-northeast1-c"),
        ("Osaka (asia-northeast2-a)", "asia-northeast2-a"),
        ("Osaka (asia-northeast2-b)", "asia-northeast2-b"),
        ("Osaka (asia-northeast2-c)", "asia-northeast2-c"),
        ("Seoul (asia-northeast3-a)", "asia-northeast3-a"),
        ("Seoul (asia-northeast3-b)", "asia-northeast3-b"),
        ("Seoul (asia-northeast3-c)", "asia-northeast3-c"),
    ]

    def __init__(self, parent: MainWindow) -> None:
        super().__init__()

        self.parent = parent
        self.zone_id: str | None = None
        self.instance: Instance | None = None

        self.init_widgets()
        self.init_workers()

    def init_widgets(self) -> None:
        layout = QVBoxLayout()
        layout.addLayout(self.init_project_and_zone())
        layout.addItem(QSpacerItem(0, 10))
        layout.addWidget(HLine())
        layout.addItem(QSpacerItem(0, 10))
        layout.addLayout(self.init_instances())

        self.setLayout(layout)

    def init_project_and_zone(self) -> QLayout:
        self.input_project = ReadOnlyLineEdit()

        layout_project = QHBoxLayout()
        layout_project.addWidget(QLabel("Project ID"))
        layout_project.addWidget(self.input_project)

        self.select_zone = QComboBox()
        self.select_zone.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.select_zone.currentIndexChanged.connect(self.select_zone_item_changed)

        layout_zone = QHBoxLayout()
        layout_zone.addWidget(QLabel("Zone"))
        layout_zone.addWidget(self.select_zone)

        layout = QHBoxLayout()
        layout.addLayout(layout_project)
        layout.addItem(QSpacerItem(10, 0))
        layout.addLayout(layout_zone)

        return layout

    def init_instances(self) -> QLayout:
        button_list_instances = QPushButton("List Instances")
        button_list_instances.clicked.connect(self.button_list_instances_clicked)

        button_create_instance = QPushButton("Create Instance")
        button_create_instance.clicked.connect(self.button_create_instance_clicked)

        layout_instance_buttons = QHBoxLayout()
        layout_instance_buttons.addWidget(button_list_instances)
        layout_instance_buttons.addWidget(button_create_instance)

        self.list_instances = QListWidget()
        self.list_instances.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_instances.currentItemChanged.connect(self.list_instances_item_changed)
        self.list_instances.customContextMenuRequested.connect(self.list_instances_context_menu_requested)

        layout_instances = QVBoxLayout()
        layout_instances.addLayout(layout_instance_buttons)
        layout_instances.addItem(QSpacerItem(0, 10))
        layout_instances.addWidget(self.list_instances)

        self.input_instance_name = ReadOnlyLineEdit()
        self.input_instance_id = ReadOnlyLineEdit()
        self.input_instance_description = ReadOnlyLineEdit()
        self.input_instance_status = ReadOnlyLineEdit()
        self.input_instance_creation_time = ReadOnlyLineEdit()
        self.input_instance_zone = ReadOnlyLineEdit()
        self.input_instance_hostname = ReadOnlyLineEdit()
        self.input_instance_machine_type = ReadOnlyLineEdit()
        self.input_instance_cpu_platform = ReadOnlyLineEdit()
        self.input_instance_architecture = ReadOnlyLineEdit()
        self.input_instance_network_interface = ReadOnlyLineEdit()
        self.input_instance_network = ReadOnlyLineEdit()
        self.input_instance_subnetwork = ReadOnlyLineEdit()
        self.input_instance_stack_type = ReadOnlyLineEdit()
        self.input_instance_network_tier = ReadOnlyLineEdit()
        self.input_instance_internal_ip = ReadOnlyLineEdit()
        self.input_instance_external_ip = ReadOnlyLineEdit()
        self.input_instance_disk = ReadOnlyLineEdit()
        self.input_instance_disk_size = ReadOnlyLineEdit()
        self.input_instance_image = ReadOnlyLineEdit()

        layout_instance = QFormLayout()
        layout_instance.addRow(Heading("Basic Information", 6, "bold"))
        layout_instance.addItem(QSpacerItem(0, 6))
        layout_instance.addRow("Name", self.input_instance_name)
        layout_instance.addRow("ID", self.input_instance_id)
        layout_instance.addRow("Description", self.input_instance_description)
        layout_instance.addRow("Status", self.input_instance_status)
        layout_instance.addRow("Creation Time", self.input_instance_creation_time)
        layout_instance.addRow("Zone", self.input_instance_zone)
        layout_instance.addRow("Hostname", self.input_instance_hostname)
        layout_instance.addItem(QSpacerItem(0, 6))
        layout_instance.addRow(Heading("Machine Configuration", 6, "bold"))
        layout_instance.addItem(QSpacerItem(0, 6))
        layout_instance.addRow("Machine Type", self.input_instance_machine_type)
        layout_instance.addRow("CPU Platform", self.input_instance_cpu_platform)
        layout_instance.addRow("Architecture", self.input_instance_architecture)
        layout_instance.addItem(QSpacerItem(0, 6))
        layout_instance.addRow(Heading("Network Interface", 6, "bold"))
        layout_instance.addItem(QSpacerItem(0, 6))
        layout_instance.addRow("Interface", self.input_instance_network_interface)
        layout_instance.addRow("Network", self.input_instance_network)
        layout_instance.addRow("Subnetwork", self.input_instance_subnetwork)
        layout_instance.addRow("Stack Type", self.input_instance_stack_type)
        layout_instance.addRow("Network Tier", self.input_instance_network_tier)
        layout_instance.addRow("Internal IP", self.input_instance_internal_ip)
        layout_instance.addRow("External IP", self.input_instance_external_ip)
        layout_instance.addItem(QSpacerItem(0, 6))
        layout_instance.addRow(Heading("Storage", 6, "bold"))
        layout_instance.addItem(QSpacerItem(0, 6))
        layout_instance.addRow("Disk", self.input_instance_disk)
        layout_instance.addRow("Disk Size (GB)", self.input_instance_disk_size)
        layout_instance.addRow("Image", self.input_instance_image)

        self.area_instance = QWidget()
        self.area_instance.setLayout(layout_instance)

        widget_instance = QScrollArea()
        widget_instance.setWidget(self.area_instance)
        widget_instance.setWidgetResizable(True)

        button_refresh = QPushButton("Refresh")
        button_refresh.clicked.connect(self.list_instances_item_changed)

        button_start_instance = QPushButton("Start")
        button_start_instance.clicked.connect(self.button_start_instance_clicked)

        button_resume_instance = QPushButton("Resume")
        button_resume_instance.clicked.connect(self.button_resume_instance_clicked)

        button_stop_instance = QPushButton("Stop")
        button_stop_instance.clicked.connect(self.button_stop_instance_clicked)

        button_suspend_instance = QPushButton("Suspend")
        button_suspend_instance.clicked.connect(self.button_suspend_instance_clicked)

        button_reset_instance = QPushButton("Reset")
        button_reset_instance.clicked.connect(self.button_reset_instance_clicked)

        button_delete_instance = QPushButton("Delete")
        button_delete_instance.clicked.connect(self.button_delete_instance_clicked)

        button_set_instance_tags = QPushButton("Set Tags")
        button_set_instance_tags.clicked.connect(self.button_set_instance_tags_clicked)

        button_set_instance_metadata = QPushButton("Set Metadata")
        button_set_instance_metadata.clicked.connect(self.button_set_instance_metadata_clicked)

        layout_operations = QVBoxLayout()
        layout_operations.addWidget(button_refresh)
        layout_operations.addItem(QSpacerItem(0, 10))
        layout_operations.addWidget(HLine())
        layout_operations.addItem(QSpacerItem(0, 10))
        layout_operations.addWidget(button_start_instance)
        layout_operations.addWidget(button_resume_instance)
        layout_operations.addWidget(button_stop_instance)
        layout_operations.addWidget(button_suspend_instance)
        layout_operations.addWidget(button_reset_instance)
        layout_operations.addWidget(button_delete_instance)
        layout_operations.addItem(QSpacerItem(0, 10))
        layout_operations.addWidget(HLine())
        layout_operations.addItem(QSpacerItem(0, 10))
        layout_operations.addWidget(button_set_instance_tags)
        layout_operations.addWidget(button_set_instance_metadata)
        layout_operations.addStretch()

        self.widget_operations = QWidget()
        self.widget_operations.setLayout(layout_operations)
        self.widget_operations.setDisabled(True)

        layout = QHBoxLayout()
        layout.addLayout(layout_instances, 2)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(VLine())
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(widget_instance, 3)
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(VLine())
        layout.addItem(QSpacerItem(10, 0))
        layout.addWidget(self.widget_operations, 1)

        return layout

    def init_workers(self) -> None:
        self.worker_load_instance_list = LoadInstanceListWorker()
        self.worker_load_instance_list.completed.connect(self.load_instance_list)
        self.worker_load_instance_list.failed.connect(self.handle_worker_exception)

        self.worker_load_instance_details = LoadInstanceDetailsWorker()
        self.worker_load_instance_details.completed.connect(self.load_instance_details)
        self.worker_load_instance_details.failed.connect(self.handle_worker_exception)

        self.worker_create_instance = CreateInstanceWorker()
        self.worker_create_instance.created.connect(self.wait_for_extended_operation)
        self.worker_create_instance.completed.connect(self.instance_created)
        self.worker_create_instance.failed.connect(self.handle_worker_exception)

        self.worker_start_instance = StartInstanceWorker()
        self.worker_start_instance.started.connect(self.wait_for_extended_operation)
        self.worker_start_instance.completed.connect(self.instance_started)
        self.worker_start_instance.failed.connect(self.handle_worker_exception)

        self.worker_resume_instance = ResumeInstanceWorker()
        self.worker_resume_instance.resumed.connect(self.wait_for_extended_operation)
        self.worker_resume_instance.completed.connect(self.instance_resumed)
        self.worker_resume_instance.failed.connect(self.handle_worker_exception)

        self.worker_stop_instance = StopInstanceWorker()
        self.worker_stop_instance.stopped.connect(self.wait_for_extended_operation)
        self.worker_stop_instance.completed.connect(self.instance_stopped)
        self.worker_stop_instance.failed.connect(self.handle_worker_exception)

        self.worker_suspend_instance = SuspendInstanceWorker()
        self.worker_suspend_instance.suspended.connect(self.wait_for_extended_operation)
        self.worker_suspend_instance.completed.connect(self.instance_suspended)
        self.worker_suspend_instance.failed.connect(self.handle_worker_exception)

        self.worker_reset_instance = ResetInstanceWorker()
        self.worker_reset_instance.reset.connect(self.wait_for_extended_operation)
        self.worker_reset_instance.completed.connect(self.instance_reset)
        self.worker_reset_instance.failed.connect(self.handle_worker_exception)

        self.worker_delete_instance = DeleteInstanceWorker()
        self.worker_delete_instance.deleted.connect(self.wait_for_extended_operation)
        self.worker_delete_instance.completed.connect(self.instance_deleted)
        self.worker_delete_instance.failed.connect(self.handle_worker_exception)

        self.worker_set_instance_tags = SetInstanceTagsWorker()
        self.worker_set_instance_tags.set.connect(self.wait_for_extended_operation)
        self.worker_set_instance_tags.completed.connect(self.instance_tags_set)
        self.worker_set_instance_tags.failed.connect(self.handle_worker_exception)

        self.worker_set_instance_metadata = SetInstanceMetadataWorker()
        self.worker_set_instance_metadata.set.connect(self.wait_for_extended_operation)
        self.worker_set_instance_metadata.completed.connect(self.instance_metadata_set)
        self.worker_set_instance_metadata.failed.connect(self.handle_worker_exception)

    def update_widgets(self) -> None:
        self.input_project.setText(self.parent.project_id)

        for zone, zone_id in self.ZONES:
            self.select_zone.addItem(zone, zone_id)

    def handle_worker_exception(self, e: GoogleAPICallError) -> None:
        QMessageBox.critical(
            self,
            "Error Occurred",
            e.errors[0]["message"]
        )

        self.parent.statusBar().showMessage("Error occurred: " + e.errors[0]["message"])
        self.parent.page_loading.fade_out()
        self.parent.stack.unblur()

    def wait_for_extended_operation(self) -> None:
        self.parent.statusBar().showMessage("Waiting for extended operation...")
        self.parent.page_loading.set_loading_message("Waiting for extended operation...")
        
    def select_zone_item_changed(self) -> None:
        self.zone_id = self.select_zone.currentData()
        self.button_list_instances_clicked()

    def button_list_instances_clicked(self) -> None:
        self.parent.statusBar().showMessage("Loading instance list...")
        self.parent.page_loading.set_loading_message("Loading instance list...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.list_instances.clear()

        for widget in self.area_instance.findChildren(QLineEdit):  # type: QLineEdit
            widget.clear()

        self.worker_load_instance_list.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id
        })
        self.worker_load_instance_list.start()

    def load_instance_list(self, instances: Iterable[Instance]) -> None:
        self.list_instances.addItems([instance.name for instance in instances])

        self.parent.statusBar().showMessage("Instance list loaded.")
        self.parent.page_loading.fade_out()
        self.parent.stack.unblur()

    def list_instances_item_changed(self) -> None:
        self.instance = None

        for widget in self.area_instance.findChildren(QLineEdit):  # type: QLineEdit
            widget.clear()

        self.widget_operations.setDisabled(True)

        if self.list_instances.currentItem():
            self.parent.statusBar().showMessage("Loading instance details...")
            self.parent.page_loading.set_loading_message("Loading instance details...")
            self.parent.page_loading.fade_in()
            self.parent.stack.blur()

            self.worker_load_instance_details.set_args({
                "project": self.parent.project_id,
                "zone": self.zone_id,
                "instance_name": self.list_instances.currentItem().text()
            })
            self.worker_load_instance_details.start()

    def load_instance_details(self, instance: Instance) -> None:
        self.instance = instance

        instance_details = {
            "name": instance.name,
            "id": instance.id,
            "description": instance.description,
            "status": instance.status,
            "creation_time": datetime.datetime.fromisoformat(instance.creation_timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "zone": instance.zone.split("/")[-1],

            "hostname": instance.hostname,
            "machine_type": instance.machine_type.split("/")[-1],
            "cpu_platform": instance.cpu_platform,
            "architecture": instance.disks[0].architecture,

            "network_interface": instance.network_interfaces[0].name,
            "network": instance.network_interfaces[0].network.split("/")[-1],
            "subnetwork": instance.network_interfaces[0].subnetwork.split("/")[-1],
            "stack_type": instance.network_interfaces[0].stack_type,
            "network_tier": instance.network_interfaces[0].access_configs[0].network_tier,
            "internal_ip": instance.network_interfaces[0].network_i_p,
            "external_ip": instance.network_interfaces[0].access_configs[0].nat_i_p,

            "disk": instance.disks[0].device_name,
            "disk_size": instance.disks[0].disk_size_gb,
            "image": "/".join(instance.disks[0].licenses[0].split("/")[5:])
        }

        for field, value in instance_details.items():
            getattr(self, f"input_instance_{field}").setText(str(value))

        self.widget_operations.setEnabled(True)

        self.parent.statusBar().showMessage("Instance details loaded.")
        self.parent.page_loading.fade_out()
        self.parent.stack.unblur()

    def list_instances_context_menu_requested(self, position: QPoint):
        def start_ssh() -> None:
            self.parent.menu_bar.show_ssh_client_window()
            self.parent.menu_bar.window_ssh.page_connect.input_host.setText(
                self.instance.network_interfaces[0].access_configs[0].nat_i_p
            )

            for metadata in self.instance.metadata.items:
                if metadata.key == "ssh-keys":
                    self.parent.menu_bar.window_ssh.page_connect.input_username.setText(metadata.value.split(":")[0])
                    self.parent.menu_bar.window_ssh.page_connect.button_key.click()

        if (item := self.list_instances.itemAt(position)) and item.isSelected() and self.instance:
            menu = QMenu()
            menu.addAction("SSH", start_ssh)
            menu.exec(self.list_instances.mapToGlobal(position))

    def button_create_instance_clicked(self) -> None:
        dialog = CreateInstanceDialog()

        if not dialog.exec():
            return

        self.parent.statusBar().showMessage("Creating instance...")
        self.parent.page_loading.set_loading_message("Creating instance...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_create_instance.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            **dialog.instance_info
        })
        self.worker_create_instance.start()

    def instance_created(self) -> None:
        self.button_list_instances_clicked()

    def button_start_instance_clicked(self) -> None:
        self.parent.statusBar().showMessage("Starting instance...")
        self.parent.page_loading.set_loading_message("Starting instance...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_start_instance.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name
        })
        self.worker_start_instance.start()

    def instance_started(self) -> None:
        self.list_instances_item_changed()

    def button_resume_instance_clicked(self) -> None:
        self.parent.statusBar().showMessage("Resuming instance...")
        self.parent.page_loading.set_loading_message("Resuming instance...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_resume_instance.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name
        })
        self.worker_resume_instance.start()

    def instance_resumed(self) -> None:
        self.list_instances_item_changed()

    def button_stop_instance_clicked(self) -> None:
        result = QMessageBox.question(
            self,
            "Stop Instance",
            """You'll be billed only for these preserved resources:

 · Persistent disks
 · Static IP addresses

The VM will gracefully shut down in 90 seconds. If processes are still running, the VM will be forced to stop and files may get corrupted.""",
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self.parent.statusBar().showMessage("Stopping instance...")
        self.parent.page_loading.set_loading_message("Stopping instance...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_stop_instance.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name
        })
        self.worker_stop_instance.start()

    def instance_stopped(self) -> None:
        self.list_instances_item_changed()

    def button_suspend_instance_clicked(self) -> None:
        result = QMessageBox.question(
            self,
            "Suspend Instance",
            """You'll be billed only for these preserved resources:

 · Persistent disks
 · VM memory stored in persistent disks
 · Static IP addresses""",
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self.parent.statusBar().showMessage("Suspending instance...")
        self.parent.page_loading.set_loading_message("Suspending instance...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_suspend_instance.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name
        })
        self.worker_suspend_instance.start()

    def instance_suspended(self) -> None:
        self.list_instances_item_changed()

    def button_reset_instance_clicked(self) -> None:
        result = QMessageBox.question(
            self,
            "Reset Instance",
            "Reset performs a hard reset on the instance, which wipes the memory contents of the machine and resets "
            "the virtual machine to its initial state. This can lead to filesystem corruption. Do you want to reset "
            f"\"{self.input_instance_name.text()}\"?",
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self.parent.statusBar().showMessage("Resetting instance...")
        self.parent.page_loading.set_loading_message("Resetting instance...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_reset_instance.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name
        })
        self.worker_reset_instance.start()

    def instance_reset(self) -> None:
        self.list_instances_item_changed()

    def button_delete_instance_clicked(self) -> None:
        result = QMessageBox.question(
            self,
            "Delete Instance",
            f"Are you sure you want to delete instance \"{self.input_instance_name.text()}\"?",
            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self.parent.statusBar().showMessage("Deleting instance...")
        self.parent.page_loading.set_loading_message("Deleting instance...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_delete_instance.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name
        })
        self.worker_delete_instance.start()

    def instance_deleted(self) -> None:
        self.button_list_instances_clicked()

    def button_set_instance_tags_clicked(self) -> None:
        dialog = SetInstanceTagsDialog()
        dialog.tags = deepcopy(self.instance.tags)
        dialog.update_widgets()

        if not dialog.exec():
            return

        self.parent.statusBar().showMessage("Setting tags...")
        self.parent.page_loading.set_loading_message("Setting tags...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_set_instance_tags.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name,
            "tags": dialog.tags
        })
        self.worker_set_instance_tags.start()

    def instance_tags_set(self) -> None:
        self.list_instances_item_changed()

    def button_set_instance_metadata_clicked(self) -> None:
        dialog = SetInstanceMetadataDialog()
        dialog.metadata = deepcopy(self.instance.metadata)
        dialog.update_widgets()

        if not dialog.exec():
            return

        self.parent.statusBar().showMessage("Setting metadata...")
        self.parent.page_loading.set_loading_message("Setting metadata...")
        self.parent.page_loading.fade_in()
        self.parent.stack.blur()

        self.worker_set_instance_metadata.set_args({
            "project": self.parent.project_id,
            "zone": self.zone_id,
            "instance_name": self.instance.name,
            "metadata": dialog.metadata
        })
        self.worker_set_instance_metadata.start()

    def instance_metadata_set(self) -> None:
        self.list_instances_item_changed()
