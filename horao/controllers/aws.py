# -*- coding: utf-8 -*-#
"""Controller for synchronization infrastructural state with AWS.
Notes:
    One should configure the AWS credentials via the AWS CLI or AWS environment variables.
    We assume that the resources in AWS are tagged with a specific tag and value specified in the configuration.
    We will treat each AZ in each region that has these tagged resources as a separate DataCenter object.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import boto3  # type: ignore
from botocore.client import BaseClient  # type: ignore

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
        self.logger = logging.getLogger(__name__)
        aws_file = os.getenv("AWS_CONFIG_FILE")
        if not aws_file:
            raise RuntimeError("AWS_CONFIG_FILE environment variable not set")
        aws_tag = os.getenv("AWS_TAG")
        if not aws_tag:
            raise RuntimeError("AWS_TAG environment variable not set")
        aws_tag_value = os.getenv("AWS_TAG_VALUE")
        if not aws_tag_value:
            raise RuntimeError("AWS_TAG_VALUE environment variable not set")
        self.aws_regions = os.getenv("AWS_REGIONS")
        if not self.aws_regions:
            self.logger.warning(
                "AWS_REGIONS environment variable not set, using default region"
            )
        else:
            self.aws_regions = self.aws_regions.split(",")
        self.custom_filter = [{"Name": f"tag:{aws_tag}", "Values": [aws_tag_value]}]

    def sync(self) -> None:
        """
        Synchronize AWS resource utilization to local structure.
        Currently each AZ has one row per VPC with one cabinet,
        this may change in the future.
        Todo: currently only ec2, need to add network and storage
        :return: None
        :raises RuntimeError: if instance type not found
        """

        def internal_sync(r: Optional[str]) -> None:
            client = (
                boto3.client("ec2") if not r else boto3.client("ec2", region_name=r)
            )
            response = client.describe_instances(Filters=self.custom_filter)
            restructured = self.enumerate_machines(client, response)
            for composed in restructured.keys():
                dc, vpc = composed.split(":")
                datacenter = next(
                    iter([d for d in self.datacenters.keys() if d.name == dc]), None
                )
                if not datacenter:
                    self.datacenters[
                        DataCenter(
                            dc,
                            len(self.datacenters),
                        )
                    ] = []
                    datacenter = next(
                        iter([d for d in self.datacenters.keys() if d.name == dc]),
                        None,
                    )
                cabinet = None
                row_nr = 1
                for nr, cabinets in datacenter.values():  # type: ignore
                    # one cabinet per VPC
                    for c in cabinets:  # type: ignore
                        if c.name == vpc:
                            cabinet = c
                            break
                    row_nr = nr  # type: ignore
                if not cabinet:
                    datacenter[row_nr + 1] = [  # type: ignore
                        Cabinet("AWS", vpc, "cloud", len(datacenter) + 1, restructured[dc], [], [])  # type: ignore
                    ]
                else:
                    for server in restructured[dc]:
                        if server not in cabinet.servers:
                            cabinet.servers.append(server)
                    for server in cabinet.servers:
                        if server not in restructured[dc]:
                            cabinet.servers.remove(server)

        if self.aws_regions:
            for region in self.aws_regions:
                internal_sync(region)
        else:
            internal_sync(None)

    def enumerate_machines(
        self, client: BaseClient, response: Any, region: Optional[str] = None
    ) -> Dict[str, List[Server]]:
        """
        Enumerate all machines in the response.
        Will create a dictionary of key: AWS-({REGION}-)AZ:VPCID with a list of servers as value.
        :param client: botoclient
        :param response: client response
        :param region: optional region
        :return: dict of specific VPCID key with list of Server as value
        :raises RuntimeError: if instance type not found
        """
        restructured: Dict[str, List[Server]] = {}
        for reservation in response["Reservations"]:
            # todo needs optimization
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
                placement_key = (
                    f'AWS-{instance["Placement"]["AvailabilityZone"]}'
                    if not region
                    else f'AWS-{region}-{instance["Placement"]["AvailabilityZone"]}'
                )
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
                if placement_key not in [d.name for d in self.datacenters.keys()]:
                    self.datacenters[
                        DataCenter(
                            placement_key,
                            len(self.datacenters),
                        )
                    ] = []
                if f'{placement_key}:{instance["VpcId"]}' not in restructured.keys():
                    restructured[f'{placement_key}:{instance["VpcId"]}'] = []
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
                            break
                    nics.append(
                        NIC(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-NIC',
                            int(instance_type["NetworkInfo"]["NetworkCardIndex"]),
                            [
                                Port(
                                    f'AWS-{instance["InstanceType"]}',
                                    f'AWS-{instance["InstanceType"]}-NIC-PORT',
                                    1,
                                    mac,
                                    status,
                                    True,
                                    int(network_interface["PeakBandwidthInGbps"]),
                                )
                            ],
                        )
                    )
                disks: List[Disk] = []
                for block_device in instance_type["InstanceStorageInfo"]["Disks"]:
                    disks.append(
                        Disk(
                            f'AWS-{instance["InstanceType"]}',
                            f'AWS-{instance["InstanceType"]}-DISK',
                            len(disks) + 1,
                            int(block_device["SizeInGB"]),
                        )
                    )
                accelerators: List[Accelerator] = []
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
                restructured[f'{placement_key}:{instance["VpcId"]}'].append(
                    Server(
                        instance["InstanceId"],
                        instance["InstanceId"],
                        instance["InstanceType"],
                        len(
                            restructured[
                                f'{instance["Placement"]["AvailabilityZone"]}:{instance["VpcId"]}'
                            ]
                        )
                        + 1,
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
        return restructured

    def subscribe(self):
        """Subscribe to AWS updates dynamically."""
        raise NotImplementedError("Subscribe to AWS updates not implemented yet")
