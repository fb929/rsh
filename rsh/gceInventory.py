#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import inspect
import logging
import json

from .common import CommonMixin

class gceInventory(
    CommonMixin,
    ):
    def __init__(self, cfg):
        self.logger = logging.getLogger(__name__)
        self.cfg = cfg

    def instancesInfo(self):
        """
        return info for all instances
        example:
        [
            {
                "host": "ctl.gc",
                "dc": "europe-west4-c",
                "PrivateIpAddress": "10.12.0.193",
                "PublicIpAddress": "34.13.233.212",
                "tags": [
                    {
                        "Key": "managed_by",
                        "Value": "puppet"
                    },
                    {
                        "Key": "name",
                        "Value": "ctl"
                    }
                ],
                "rshInventoryModule": "gceInventory",
                "hosting": "gce",
                "sshHost": "10.12.0.193"
            }
        ]
        """

        defName = inspect.stack()[0][3]

        instancesInfoArray = list()
        describeInstances = self.runCmd("gcloud compute instances list --format=json")['stdout']
        for describeInstance in describeInstances:
            name = describeInstance['name']
            if self.cfg['gceInventory']['nameSuffix']:
                # set name suffix if need
                name = name + self.cfg['gceInventory']['nameSuffix']
            status = describeInstance['status']
            if self.cfg['gceInventory']['skipNotRunningInstance']:
                if status != 'RUNNING':
                    self.logger.DEBUG(f"{defName}: skipping instance name='{name}', because its status is not 'RUNNING'")
                    continue
            zone = describeInstance['zone']
            dc = zone.split('/')[-1]
            PrivateIpAddress = describeInstance['networkInterfaces'][0]['networkIP']
            PublicIpAddress = describeInstance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
            tags = list()
            for item in describeInstance['metadata']['items']:
                if item['key'] == 'startup-script':
                    # skipping startup-script metadata
                    continue
                else:
                    tags.append({ "Key": item['key'], "Value": item['value'] })

            info = {
                "host": name,
                "dc": dc,
                "PrivateIpAddress": PrivateIpAddress,
                "PublicIpAddress": PublicIpAddress,
                "tags": tags,
            }

            # added rsh inventory info
            info['rshInventoryModule'] = self.__class__.__name__
            info['hosting'] = 'gce'

            # added sshHost tag
            info['sshHost'] = info.get(self.cfg['gceInventory']['sshHostField'], 'unknown')
            instancesInfoArray.append(info)

        return instancesInfoArray
