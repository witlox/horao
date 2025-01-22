# -*- coding: utf-8 -*-#
"""Controller for synchronization infrastructural state with GCP.
Notes:
    One should configure the GCP credentials via the Google Cloud CLI or Google Cloud environment variables.
    We assume that the resources in GCP are assigned to a specific project using a specific Tag.
    We will treat each zone a separate DataCenter object.
"""
from __future__ import annotations

import os

from google.cloud import compute_v1

from horao.controllers.base import BaseController
from horao.physical.component import CPU, RAM, Accelerator, Disk
from horao.physical.composite import Cabinet
from horao.physical.network import NIC, Port
from horao.physical.status import DeviceStatus


class GoogleCloudController(BaseController):
    def __init__(self, datacenters):
        super().__init__(datacenters)
        self.project_id = os.getenv("GCP_PROJECT_ID")
        if not self.project_id:
            raise RuntimeError("GCP_PROJECT_ID environment variable not set")
        self.tag = os.getenv("GCP_TAG")
        if not self.tag:
            raise RuntimeError("GCP_TAG environment variable not set")

    def sync(self):
        instance_client = compute_v1.InstancesClient()
        request = compute_v1.AggregatedListInstancesRequest()
        request.project = self.project_id
        agg_list = instance_client.aggregated_list(request=request)
        # first loop to fetch machine types
        mt_request = compute_v1.AggregatedListMachineTypesRequest()
        mt_agg_list = instance_client.aggregated_list(request=mt_request)
        instance_types = []
        # todo needs optimization
        for zone, response in agg_list:
            if response.instances:
                for instance in response.instances:
                    if self.tag not in instance.tags:
                        continue
                    for n, r in mt_agg_list:
                        for mt in r.machine_types:
                            if instance.machineType == mt.name:
                                instance_types.append(mt)
                                break

        # second loop to fetch instances
        restructured = {}
        for zone, response in agg_list:
            if response.instances:
                placement_key = f"GCP-{zone}"
                if placement_key not in restructured.keys():
                    restructured[placement_key] = []
                for instance in response.instances:
                    if self.tag not in instance.tags:
                        continue
                    cpus = [
                        CPU(
                            f"GCP-{instance.machineType}",
                            f"GCP-{instance.machineType}-CPU",
                            i,
                            1,
                            1,
                            None,
                        )
                        for i in range(
                            1, int(instance_types[instance.machineType].guestCpus)
                        )
                    ]
                    rams = [
                        RAM(
                            f"GCP-{instance.machineType}",
                            f"GCP-{instance.machineType}-RAM",
                            1,
                            instance_types[instance.machineType].memoryMb // 1024,
                            None,
                        )
                    ]
                    nics = []
                    for i, network_interface in enumerate(instance.networkInterfaces):
                        nics.append(
                            NIC(
                                f"GCP-{instance.machineType}",
                                f"GCP-{instance.machineType}-NIC",
                                i + 1,
                                [
                                    Port(
                                        f"GCP-{instance.machineType}",
                                        f"GCP-{instance.machineType}-NIC-PORT",
                                        1,
                                        "unknown::gcp",
                                        DeviceStatus.Up,  # todo actual status?
                                        True,
                                        100,  # todo again actual speed?
                                    )
                                ],
                            )
                        )
                    disks = []
                    for i, disk in enumerate(instance.disks):
                        disks.append(
                            Disk(
                                f"GCP-{instance.machineType}",
                                f"GCP-{instance.machineType}-DISK",
                                i + 1,
                                disk.diskSizeGb,
                            )
                        )
                    accelerators = []
                    for i, accelerator in enumerate(
                        instance_types[instance.machineType].guestAccelerators
                    ):
                        for j in range(1, accelerator.count):
                            accelerators.append(
                                Accelerator(
                                    f"GCP-{accelerator.guestAcceleratorType}",
                                    f"GCP-{accelerator.acceleratorType}",
                                    j,
                                    0,
                                    "unknown::gcp",
                                    None,
                                )
                            )
                    restructured[placement_key].append(
                        {
                            "serial_number": instance.id,
                            "name": instance.name,
                            "model": instance.machineType,
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
                    Cabinet("GCP", zone, "cloud", 1, restructured[composed], [], [])
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
