from typing import Any
from abc import abstractmethod
import socket

from PySide6.QtCore import QThread, Signal
from google.api_core.exceptions import GoogleAPICallError
from paramiko import SSHClient, SSHException
from paramiko.channel import ChannelFile
from pyte import Screen, Stream

from cloud import GoogleCloudClient


class GoogleCloudWorker(QThread):
    completed = Signal(Any)
    failed = Signal(GoogleAPICallError)

    def __init__(self, google_cloud_client: GoogleCloudClient = None) -> None:
        super().__init__()

        self.google_cloud_client = google_cloud_client or GoogleCloudClient.default_client
        self.args = {}

    def set_args(self, args: dict) -> None:
        self.args = args

    @abstractmethod
    def work(self) -> None:
        pass

    def run(self) -> None:
        try:
            self.work()
        except GoogleAPICallError as e:
            self.failed.emit(e)


class LoadInstanceListWorker(GoogleCloudWorker):
    def work(self) -> None:
        instances = self.google_cloud_client.list_instances(**self.args)
        self.completed.emit(instances)


class LoadInstanceDetailsWorker(GoogleCloudWorker):
    def work(self) -> None:
        instance = self.google_cloud_client.get_instance(**self.args)
        self.completed.emit(instance)


class CreateInstanceWorker(GoogleCloudWorker):
    created = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.create_instance(**self.args)
        self.created.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class StartInstanceWorker(GoogleCloudWorker):
    started = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.start_instance(**self.args)
        self.started.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class ResumeInstanceWorker(GoogleCloudWorker):
    resumed = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.resume_instance(**self.args)
        self.resumed.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class StopInstanceWorker(GoogleCloudWorker):
    stopped = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.stop_instance(**self.args)
        self.stopped.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class SuspendInstanceWorker(GoogleCloudWorker):
    suspended = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.suspend_instance(**self.args)
        self.suspended.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class ResetInstanceWorker(GoogleCloudWorker):
    reset = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.reset_instance(**self.args)
        self.reset.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class DeleteInstanceWorker(GoogleCloudWorker):
    deleted = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.delete_instance(**self.args)
        self.deleted.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class SetInstanceTagsWorker(GoogleCloudWorker):
    set = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.set_instance_tags(**self.args)
        self.set.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class SetInstanceMetadataWorker(GoogleCloudWorker):
    set = Signal()

    def work(self) -> None:
        operation = self.google_cloud_client.set_instance_metadata(**self.args)
        self.set.emit()
        self.google_cloud_client.wait_for_extended_operation(operation)
        self.completed.emit(True)


class SSHWorker(QThread):
    completed = Signal(Any)
    failed = Signal(Any)

    def __init__(self) -> None:
        super().__init__()

        self.args = {}

    def set_args(self, args: dict) -> None:
        self.args = args

    @abstractmethod
    def work(self) -> None:
        pass

    def run(self) -> None:
        try:
            self.work()
        except (socket.error, SSHException) as e:
            self.failed.emit(e)


class SSHConnectWorker(SSHWorker):
    def __init__(self, ssh_client: SSHClient = None) -> None:
        super().__init__()

        self.ssh_client = ssh_client

    def work(self) -> None:
        self.ssh_client.connect(**self.args)
        self.completed.emit(True)


class SSHReadStdIOWorker(SSHWorker):
    received = Signal(str)

    def __init__(self, stdio: ChannelFile = None) -> None:
        super().__init__()

        self.stdio = stdio

    def work(self) -> None:
        screen = Screen(256, 24)
        stream = Stream(screen)

        while True:
            line = self.stdio.readline()

            if not line:
                break

            stream.feed(line)
            self.received.emit("\n".join(screen.display).strip())
            screen.reset()

        self.completed.emit(True)
