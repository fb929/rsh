#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import logging

import rsh.config
from rsh.inventory import load_inventory

logger = logging.getLogger('rshCompgen')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("An argument is required ('hosts' or 'groups').")
        sys.exit(1)

    inventory = load_inventory(rsh.config.cfg)

    arg = sys.argv[1]
    if arg == "hosts":
        hosts = list(inventory['hosts'].keys())
        print(' '.join(hosts))
    elif arg == "groups":
        groups = list(inventory['groups'].keys())
        print(' '.join(groups))
    else:
        logger.error(f"Unsupported argument '{arg}'. Only 'hosts' or 'groups' are allowed.")
        sys.exit(1)
