# -*- coding: utf-8 -*-#
"""Controller for synchronization infrastructural state with AWS.
Note that we assume that the resources in AWS are tagged with a specific tag and value specified in the configuration.
Also note that we will treat each AZ in each region that has these tagged resources as a separate DataCenter object.
"""
import json
import os

import boto3  # type: ignore

from horao.controllers.base import BaseController
from horao.logical.data_center import DataCenter
from horao.physical.component import CPU, RAM, Accelerator, Disk
from horao.physical.composite import Cabinet
from horao.physical.computer import Server
from horao.physical.network import NIC, Port
from horao.physical.status import DeviceStatus


class AmazonWebServicesController(BaseController):
    """Controller for synchronization infrastructural state with AWS."""

    def __init__(self, datacenters):
        """Initialize AWS controller."""
        super().__init__(datacenters)
        aws_file = os.getenv("AWS_CONFIG_FILE")
        if not aws_file:
            raise RuntimeError("AWS_CONFIG_FILE environment variable not set")
        aws_tag = os.getenv("AWS_TAG")
        if not aws_tag:
            raise RuntimeError("AWS_TAG environment variable not set")
        aws_tag_value = os.getenv("AWS_TAG_VALUE")
        if not aws_tag_value:
            raise RuntimeError("AWS_TAG_VALUE environment variable not set")
        self.custom_filter = [{"Name": f"tag:{aws_tag}", "Values": [aws_tag_value]}]

    def sync(self):
        """
        Synchronize AWS resource utilization to local structure.
        Currently each AZ has one row per VPC with one cabinet,
        this may change in the future.
        Todo: currently only ec2, add network and storage"""
        client = boto3.client("ec2")
        response = client.describe_instances(Filters=self.custom_filter)
        restructured = {}
        for reservation in response["Reservations"]:
            # first loop to get all instance types
            instance_types = []
            for instance in reservation["Instances"]:
                if instance["InstanceType"] not in instance_types:
                    instance_types.append(instance["InstanceType"])
            instance_types_response = client.descibe_instance_types(
                InstanceTypes=instance_types, Filters=self.custom_filter
            )
            # second loop to get all instances
            for instance in reservation["Instances"]:
                instance_type = next(
                    iter(
                        [
                            i
                            for i in instance_types_response["InstanceTypes"]
                            if instance["InstanceType"] in i["InstanceType"]
                        ]
                    ),
                    None,
                )
                if not instance_type:
                    raise RuntimeError(
                        f"Instance type {instance['InstanceType']} not found for AWS EC2"
                    )
                if f'AWS-{instance["Placement"]["AvailabilityZone"]}' not in [
                    d.name for d in self.datacenters.keys()
                ]:
                    self.datacenters[
                        DataCenter(
                            f'AWS-{instance["Placement"]["AvailabilityZone"]}',
                            len(self.datacenters),
                        )
                    ] = []
                if (
                    f'{instance["Placement"]["AvailabilityZone"]}:{instance["VpcId"]}'
                    not in restructured.keys()
                ):
                    restructured[
                        f'{instance["Placement"]["AvailabilityZone"]}:{instance["VpcId"]}'
                    ] = []
                cpus = []
                for i in range(1, int(instance_type["VCpuInfo"]["ValidCores"])):
                    cpus.append(
                        CPU(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-CPU',
                            i,
                            1,
                            1,
                            json.dumps(instance["CpuOptions"]),
                        )
                    )
                rams = [
                    RAM(
                        f'AWS-{instance["InstanceType"]}',
                        f'AWS-{instance["InstanceType"]}-RAM',
                        1,
                        int(instance_type["MemoryInfo"]["SizeInMiB"]) // 1024,
                        None,
                    )
                ]
                nics = []
                for network_interface in instance_type["NetworkInfo"]["NetworkCards"]:
                    mac = "unknown"
                    status = DeviceStatus.Down
                    for nic in instance["NetworkInterfaces"]:
                        if (
                            nic["NetworkCardIndex"]
                            == network_interface["NetworkCardIndex"]
                        ):
                            mac = nic["MacAddress"]
                            if nic["Status"] == "in-use":
                                status = DeviceStatus.Up
                    nics.append(
                        NIC(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-NIC',
                            int(instance_type["NetworkInfo"]["NetworkCardIndex"]),
                            [
                                Port(
                                    f'AWS-{instance["InstanceType"]}',
                                    f'AWS-{instance["InstanceType"]}-NIC-PORT',
                                    len(nics) + 1,
                                    mac,
                                    status,
                                    True,
                                    int(network_interface["PeakBandwidthInGbps"]),
                                )
                            ],
                        )
                    )
                disks = []
                for block_device in instance_type["InstanceStorageInfo"]["Disks"]:
                    disks.append(
                        Disk(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-DISK',
                            len(disks) + 1,
                            int(block_device["SizeInGB"]),
                        )
                    )
                accelerators = []
                for gpu in instance_type["GpuInfo"]["Gpus"]:
                    accelerators.append(
                        Accelerator(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-GPU',
                            len(accelerators) + 1,
                            gpu["MemoryInfo"]["SizeInMiB"] // 1024,
                            f'{gpu["Name"]}: {gpu["Manufacturer"]}',
                            None,
                        )
                    )
                for fpga in instance_type["FpgaInfo"]["Fpgas"]:
                    accelerators.append(
                        Accelerator(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-FPGA',
                            len(accelerators) + 1,
                            fpga["MemoryInfo"]["SizeInMiB"] // 1024,
                            f'{fpga["Name"]}: {fpga["Manufacturer"]}',
                            None,
                        )
                    )
                for ia in instance_type["InferenceAccelerators"]["Accelerators"]:
                    accelerators.append(
                        Accelerator(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-IA',
                            len(accelerators) + 1,
                            ia["MemoryInfo"]["SizeInMiB"] // 1024,
                            f'{ia["Name"]}: {ia["Manufacturer"]}',
                            None,
                        )
                    )
                restructured[
                    f'{instance["Placement"]["AvailabilityZone"]}:{instance["VpcId"]}'
                ].append(
                    Server(
                        instance["InstanceId"],
                        instance["InstanceId"],
                        instance["InstanceType"],
                        len(
                            restructured[
                                f'{instance["Placement"]["AvailabilityZone"]}:{instance["VpcId"]}'
                            ]
                        ),
                        cpus,
                        rams,
                        nics,
                        disks,
                        accelerators,
                        (
                            DeviceStatus.Up
                            if instance["State"]["name"] == "running"
                            else DeviceStatus.Down
                        ),
                    )
                )
        for composed in restructured.keys():
            dc, vpc = composed.split(":")
            datacenter = next(
                iter([d for d in self.datacenters.keys() if d.name == dc]), None
            )
            if not datacenter[1]:
                datacenter[1] = [
                    Cabinet("AWS", vpc, "cloud", 1, restructured[dc], [], [])
                ]
            else:
                for server in [d.servers for d in datacenter[0] if d.name == vpc]:
                    if server not in restructured[dc]:
                        datacenter[1][0].servers.append(server)
                for server in restructured[dc]:
                    if server not in [
                        d.servers for d in datacenter[1] if d.name == vpc
                    ]:
                        datacenter[1][0].servers.remove(server)

    def subscribe(self):
        """Subscribe to AWS."""
        pass
