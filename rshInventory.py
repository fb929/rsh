#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import rsh
import rsh.config
import logging
import json
import inspect
import re
import os
import yaml
import ovh

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    defName = "main"
    logger.debug("%s: cfg='%s'" % (defName,json.dumps(rsh.config.cfg,indent=4)))

    instancesInfoArray = list()
    # inventory plugins
    for key,value in rsh.config.cfg.items():
        if re.match(r"^.+Inventory$", key):
            inventoryConfig = rsh.config.cfg.get(key, None)
            enable = inventoryConfig.get('enable', None)
            if enable:
                # make class obj from variable {{
                klass = getattr(rsh, key)
                inventoryClass = klass(rsh.config.cfg)
                # }}
                # generate inventory dict
                instancesInfoArray.extend(inventoryClass.instancesInfo())

    logger.debug("%s: instancesInfoArray='%s'" % (defName,json.dumps(instancesInfoArray,indent=4)))

    inventory = dict()
    inventory['hosts'] = dict()
    inventory['groups'] = dict()
    for instanceInfo in instancesInfoArray:
        # hosts {{
        host = instanceInfo['host']

        # get rsh inventory module name {{
        rshInventoryModule = instanceInfo.get('rshInventoryModule', None)

        # generage "hosts" for instance
        if host not in inventory['hosts']:
            inventory['hosts'][host] = { 'sshHost': instanceInfo['sshHost'] }
            for hostInfoField in rsh.config.cfg[rshInventoryModule]['hostInfoFields']:
                inventory['hosts'][host][hostInfoField] = instanceInfo[hostInfoField]
        # }}
        # groups {{
        for tag in instanceInfo['tags']:
            if tag['Key'] in rsh.config.cfg[rshInventoryModule]['skipTagsForMakeGroups']:
                continue
            groupName = 'tag_' + tag['Key'].replace('-','_') + '_' + tag['Value'].replace('-','_')
            groupName = re.sub(r'\s+', '_', groupName)
            if groupName not in inventory['groups']:
                inventory['groups'][groupName] = list()
            if host not in inventory['groups'][groupName]:
                inventory['groups'][groupName].append(host)
        # }}
        # groups by dc {{
        hosting = instanceInfo.get('hosting', 'unknown')
        groupName = 'dc_' + hosting +'_'+ instanceInfo['dc']
        groupName = re.sub(r'\s+', '_', groupName)
        if groupName not in inventory['groups']:
            inventory['groups'][groupName] = list()
        if host not in inventory['groups'][groupName]:
            inventory['groups'][groupName].append(host)
        # }}

    # generating inventory file {{
    logger.debug("%s: inventory='%s'" % (defName,inventory))
    with open(os.path.expanduser(rsh.config.cfg['inventoryFilePath']), 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False)
    # }}
