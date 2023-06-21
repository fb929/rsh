#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import rsh.config
import yaml
import json
import os

inventory = dict()
try:
    with open(os.path.expanduser(rsh.config.cfg['inventoryFilePath']), 'r') as ymlfile:
        inventory.update(yaml.load(ymlfile,Loader=yaml.Loader))
except Exception as e:
    rsh.config.logging.error("compgen: failed inventory from file: '%s', error: '%s'" % (rsh.config.cfg['inventoryFilePath'],e))
    exit(1)

hosts = list(inventory['hosts'].keys())
print(' '.join(hosts))
