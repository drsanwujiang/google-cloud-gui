from typing import Iterable

from google.api_core.extended_operation import ExtendedOperation
from google.cloud.compute_v1 import (InstancesClient, Instance, NetworkInterface, AccessConfig, AttachedDisk,
                                     AttachedDiskInitializeParams, Tags, Metadata)


class GoogleCloudClient:
    default_client = None

    def __init__(self) -> None:
        self.instances_client: InstancesClient | None = None

    @staticmethod
    def wait_for_extended_operation(
        operation: ExtendedOperation,
        timeout: int = 300
    ):
        return operation.result(timeout=timeout)

    def load_credentials(
        self,
        credentials: dict
    ) -> None:
        self.instances_client = InstancesClient.from_service_account_info(credentials)

    def list_instances(
        self,
        project: str,
        zone: str
    ) -> Iterable[Instance]:
        return self.instances_client.list(
            project=project,
            zone=zone
        )

    def get_instance(
        self,
        project: str,
        zone: str,
        instance_name: str
    ) -> Instance:
        return self.instances_client.get(
            project=project,
            zone=zone,
            instance=instance_name
        )

    def create_instance(
        self,
        project: str,
        zone: str,
        name: str,
        description: str,
        hostname: str,
        machine_type: str,
        network_tier: str,
        disk_size: int,
        image: str
    ) -> ExtendedOperation:
        return self.instances_client.insert(
            project=project,
            zone=zone,
            instance_resource=Instance(
                name=name,
                description=description,
                hostname=hostname,
                machine_type=f"zones/{zone}/machineTypes/{machine_type}",
                network_interfaces=[
                    NetworkInterface(
                        access_configs=[
                            AccessConfig(
                                name="External NAT",
                                network_tier=network_tier
                            )
                        ]
                    )
                ],
                disks=[
                    AttachedDisk(
                        initialize_params=AttachedDiskInitializeParams(
                            disk_size_gb=disk_size,
                            source_image=image
                        ),
                        boot=True,
                        auto_delete=True
                    )
                ]
            )
        )

    def start_instance(
        self,
        project: str,
        zone: str,
        instance_name: str
    ) -> ExtendedOperation:
        return self.instances_client.start(
            project=project,
            zone=zone,
            instance=instance_name
        )

    def resume_instance(
        self,
        project: str,
        zone: str,
        instance_name: str
    ) -> ExtendedOperation:
        return self.instances_client.resume(
            project=project,
            zone=zone,
            instance=instance_name
        )

    def stop_instance(
        self,
        project: str,
        zone: str,
        instance_name: str
    ) -> ExtendedOperation:
        return self.instances_client.stop(
            project=project,
            zone=zone,
            instance=instance_name
        )

    def suspend_instance(
        self,
        project: str,
        zone: str,
        instance_name: str
    ) -> ExtendedOperation:
        return self.instances_client.suspend(
            project=project,
            zone=zone,
            instance=instance_name
        )

    def delete_instance(
        self,
        project: str,
        zone: str,
        instance_name: str
    ) -> ExtendedOperation:
        return self.instances_client.delete(
            project=project,
            zone=zone,
            instance=instance_name
        )

    def reset_instance(
        self,
        project: str,
        zone: str,
        instance_name: str
    ) -> ExtendedOperation:
        return self.instances_client.reset(
            project=project,
            zone=zone,
            instance=instance_name
        )

    def set_instance_tags(
        self,
        project: str,
        zone: str,
        instance_name: str,
        tags: Tags
    ) -> ExtendedOperation:
        return self.instances_client.set_tags(
            project=project,
            zone=zone,
            instance=instance_name,
            tags_resource=tags
        )

    def set_instance_metadata(
        self,
        project: str,
        zone: str,
        instance_name: str,
        metadata: Metadata
    ) -> ExtendedOperation:
        return self.instances_client.set_metadata(
            project=project,
            zone=zone,
            instance=instance_name,
            metadata_resource=metadata
        )


GoogleCloudClient.default_client = GoogleCloudClient()
