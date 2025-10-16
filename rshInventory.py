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

# natural sort helper:
# - split by non-alphanumeric
# - then split into alpha vs digits
# - compare strings before numbers; numbers as integers
def _natsort_tokens_key(host):
    left = str(host).split('.', 1)[0]  # strip domain part like ".aws"
    rough_tokens = re.split(r'[^A-Za-z0-9]+', left)
    tokens = []
    for t in rough_tokens:
        if not t:
            continue
        parts = re.findall(r'[A-Za-z]+|\d+', t)
        for p in parts:
            if p.isdigit():
                tokens.append((1, int(p)))
            else:
                tokens.append((0, p.lower()))
    return tokens

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
        try:
            host = instanceInfo['host']
        except:
            print(instanceInfo)
            logger.error(f"{defName}: key='host' not found in instanceInfo='{instanceInfo}'")
            exit(1)

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

    # natural sort hosts and groups {{
    # hosts: sort hostnames using token-aware natural order
    sorted_hostnames = sorted(inventory['hosts'].keys(), key=_natsort_tokens_key)
    inventory['hosts'] = { hn: inventory['hosts'][hn] for hn in sorted_hostnames }

    # groups: sort group names; inside each group sort hosts using the same key
    sorted_group_names = sorted(inventory['groups'].keys(), key=_natsort_tokens_key)
    sorted_groups = dict()
    for g in sorted_group_names:
        sorted_groups[g] = sorted(inventory['groups'][g], key=_natsort_tokens_key)
    inventory['groups'] = sorted_groups
    # }}

    # generating inventory file {{
    logger.debug("%s: inventory='%s'" % (defName,inventory))
    with open(os.path.expanduser(rsh.config.cfg['inventoryFilePath']), 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False, sort_keys=False)
    # }}
