#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/opt/rsh')
import rsh.config
import yaml
import json
import os

from rsh import exec_functions

if __name__ == "__main__":
    if len(sys.argv) < 2:
        rsh.config.logging.error("An argument is required ('hosts' or 'groups').")
        sys.exit(1)

    inventory = exec_functions.load_inventory()

    arg = sys.argv[1]
    if arg == "hosts":
        hosts = list(inventory['hosts'].keys())
        print(' '.join(hosts))
    elif arg == "groups":
        groups = list(inventory['groups'].keys())
        print(' '.join(groups))
    else:
        rsh.config.logging.error(f"Unsupported argument '{arg}'. Only 'hosts' or 'groups' are allowed.")
        sys.exit(1)
