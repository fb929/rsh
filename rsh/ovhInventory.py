#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import rsh.config
import json
import inspect
import re
import os
import yaml
import ovh
import logging

class ovhInventory():
    def __init__(self, cfg):
        self.modulePath = self.__class__.__module__
        self.className = self.__class__.__name__
        self.logger = logging.getLogger(self.modulePath+'.'+self.className)
        self.cfg = cfg

    def instancesInfo(self):
        """
        return info for all instances
        [
            {
                "sshHost": "myhost.example.com",
                "publicIp": "x.x.x.x",
                "internalName": "nsXXX.ip-X-X-X.eu",
                "dc": "unknown",
                "tags": [],
                "rshInventoryModule": "ovhInventory",
                "hosting": "ovh",
                "host": "analytics.toolpad.org"
            }
        ]
        """

        defName = inspect.stack()[0][3]

        client = ovh.Client(
            endpoint=self.cfg['ovhInventory']['api']['endpoint'],
            application_key=self.cfg['ovhInventory']['api']['application_key'],
            application_secret=self.cfg['ovhInventory']['api']['application_secret'],
            consumer_key=self.cfg['ovhInventory']['api']['consumer_key'],
        )

        dedicatedServers = client.get('/dedicated/server')

        instancesInfo = list()
        for dedicatedServer in dedicatedServers:
            info = dict()
            dedicatedServerServiceInfos = client.get(f'/dedicated/server/{dedicatedServer}/serviceInfos')
            servicesInfo = client.get('/services/%s' % dedicatedServerServiceInfos['serviceId'])
            self.logger.debug("%s: servicesInfo='%s'" % (defName, json.dumps(servicesInfo,indent=4)))
            dedicatedServerInfo = client.get(f'/dedicated/server/{dedicatedServer}')
            self.logger.debug("%s: dedicatedServerInfo='%s'" % (defName, json.dumps(dedicatedServerInfo,indent=4)))
            if dedicatedServerInfo['availabilityZone'] == 'unknown':
                dc = dedicatedServerInfo['datacenter']
            else:
                dc = dedicatedServerInfo['availabilityZone']
            infoMap = {
                'customName': servicesInfo['resource']['displayName'],
                'publicIp': dedicatedServerInfo['ip'],
                'internalName': dedicatedServerInfo['name'],
                'dc': dc,
            }
            info['sshHost'] = infoMap.get(self.cfg['ovhInventory']['sshHostField'], 'unknown')
            for hostInfoField in self.cfg['ovhInventory']['hostInfoFields']:
                info[hostInfoField] = infoMap.get(hostInfoField, 'unknown')
            if info not in instancesInfo:
                instancesInfo.append(info)

            # ovh don't have tags
            info['tags'] = []
            # added rsh inventory info {{
            info['rshInventoryModule'] = self.className
            info['hosting'] = 'ovh'
            # }}
            # set host
            info['host'] = infoMap['customName']

        return instancesInfo
