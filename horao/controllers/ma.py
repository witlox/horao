# -*- coding: utf-8 -*-#
"""Controller for synchronization infrastructural state with Azure.
Notes:
    One should configure the Microsoft Azure credentials via the Azure CLI or Azure environment variables.
    We assume that the resources in Azure are assigned to a specific subscription using a specific Tag.
    We will treat each zone a separate DataCenter object.
"""
import os

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

from horao.controllers.base import BaseController
from horao.physical.component import CPU, RAM, Accelerator, Disk
from horao.physical.composite import Cabinet
from horao.physical.network import NIC, Port
from horao.physical.status import DeviceStatus


class MicrosoftAzureController(BaseController):
    def __init__(self, datacenters):
        super().__init__(datacenters)
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not self.subscription_id:
            raise RuntimeError("AZURE_SUBSCRIPTION_ID environment variable not set")
        self.tag = os.getenv("AZURE_TAG")
        if not self.tag:
            raise RuntimeError("AZURE_TAG environment variable not set")

    def sync(self):
        client = ComputeManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )
        vm_list = client.virtual_machines.list_all()
        # first loop to fetch machine types
        instance_types = []
        for vm in vm_list:
            if self.tag not in vm.tags:
                continue
            instance_types.append(vm.hardware_profile.vm_size)
        # second loop to fetch instances
        restructured = {}
        for vm in vm_list:
            if self.tag not in vm.tags:
                continue
            placement_key = f"AZURE-{vm.location}"
            if placement_key not in restructured.keys():
                restructured[placement_key] = []
            cpus = [
                CPU(
                    vm.vm_id,
                    vm.hardware_profile.vm_size,
                    1,
                    0,
                    vm.hardware_profile.number_of_cores,
                    None,
                )
            ]
            rams = [
                RAM(
                    vm.vm_id,
                    vm.hardware_profile.vm_size,
                    1,
                    vm.hardware_profile.memory_in_mb / 1024,
                    None,
                )
            ]
            nics = []
            for i, nic in enumerate(vm.network_profile.network_interfaces):
                nics.append(
                    NIC(
                        nic.id,
                        nic.id,
                        i,
                        [
                            Port(
                                nic.id,
                                nic.id,
                                1,
                                nic.mac_address,
                                DeviceStatus.Up,  # todo get the status from Azure
                                True,
                                speed_gb=100,  # todo get the speed from Azure
                            )
                        ],
                    )
                )
            disks = []
            for i, disk in enumerate(vm.storage_profile.os_disk):
                disks.append(Disk(disk.id, disk.name, i, disk.disk_size_gb))
            accelerators = []
            # todo use resource SKUs when it becomes available in the SDK
            for i, accelerator in enumerate(vm.hardware_profile.vm_size):
                accelerators.append(
                    Accelerator(
                        accelerator.id, accelerator.name, i, 0, "unknown::azure", None
                    )
                )
            restructured[placement_key].append(
                {
                    "serial_number": vm.vm_id,
                    "name": vm.name,
                    "model": vm.hardware_profile.vm_size,
                    "number": len(restructured[placement_key]) + 1,
                    "cpus": cpus,
                    "rams": rams,
                    "nics": nics,
                    "disks": disks,
                    "accelerators": accelerators,
                }
            )
        for composed in restructured.keys():
            _, zone = composed.split("-")
            datacenter = next(
                iter([d for d in self.datacenters.keys() if d.name == zone]), None
            )
            if not datacenter[1]:
                datacenter[1] = [
                    Cabinet("AZURE", zone, "cloud", 1, restructured[composed], [], [])
                ]
            else:
                for server in [d.servers for d in datacenter[1] if d.name == zone]:
                    if server not in restructured[composed]:
                        datacenter[1][0].servers.append(server)
                for server in restructured[composed]:
                    if server not in [
                        d.servers for d in datacenter[1] if d.name == zone
                    ]:
                        datacenter[1][0].servers.remove(server)

    def subscribe(self):
        pass
