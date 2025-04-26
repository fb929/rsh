#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import rsh.config
import inspect
import re
import os
import yaml
import logging

from .common import CommonMixin

class awsInventory(
    CommonMixin,
    ):
    def __init__(self, cfg):
        self.logger = logging.getLogger(__name__)
        self.cfg = cfg

    def regionInstancesInfo(self,region):
        """
        return info for instances from one region
        """

        defName = inspect.stack()[0][3]

        instancesInfo = list()
        describeInstances = self.runCmd("aws ec2 --region %s describe-instances" % region)['stdout']
        reservations = describeInstances['Reservations']
        for reservation in reservations:
            instances = reservation['Instances']
            for instance in instances:
                if self.cfg['awsInventory']['skipNotRunningInstance']:
                    if instance['State']['Name'] != 'running':
                        continue
                try:
                    dc = instance['Placement']['AvailabilityZone']
                except:
                    self.logger.error(f"{defName}: failed get Placement.AvailabilityZone from instance={instance}")
                    exit(1)
                tags = instance.get('Tags', []) # tags is optional
                info = {
                    'dc': dc,
                    'tags': tags,
                }
                for tag in tags:
                    if tag['Key'] == 'Name':
                        info['host'] = tag['Value']

                # add default tag
                # added rsh inventory info {{
                info['rshInventoryModule'] = self.__class__.__name__
                info['hosting'] = 'aws'
                # }}

                info['sshHost'] = info.get(self.cfg['awsInventory']['sshHostField'], 'unknown')
                for hostInfoField in self.cfg['awsInventory']['hostInfoFields']:
                    info[hostInfoField] = instance.get(hostInfoField, 'unknown')
                if info not in instancesInfo:
                    instancesInfo.append(info)
        return instancesInfo

    def instancesInfo(self):
        """
        return info for all instances
        example:
        [
            {
                "dc": "eu-central-2c",
                "tags": [
                    {
                        "Key": "role",
                        "Value": "prod"
                    },
                    {
                        "Key": "group",
                        "Value": "prod-redis"
                    },
                    {
                        "Key": "Name",
                        "Value": "prod-redis1"
                    },
                    {
                        "Key": "managed_by",
                        "Value": "puppet"
                    }
                ],
                "host": "prod-redis1",
                "rshInventoryModule": "awsInventory",
                "hosting": "aws",
                "sshHost": "172.33.33.13",
                "PrivateIpAddress": "172.33.33.13",
                "PublicIpAddress": "8.8.8.8"
            }
        ]
        """

        defName = inspect.stack()[0][3]

        if self.cfg['awsInventory']['regions']:
            regions = self.cfg['awsInventory']['regions']
        else:
            regions = self.runCmd("aws ec2 describe-regions --query 'Regions[].RegionName'")['stdout']
        self.logger.debug("%s: regions='%s'" % (defName,regions))
        instancesInfoArray = list()
        for region in regions:
            instancesInfoArray = instancesInfoArray + self.regionInstancesInfo(region)
        return instancesInfoArray
