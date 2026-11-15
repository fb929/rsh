#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for reading the generated inventory file (inventory.yaml).

Inventory layout:
    hosts:
      <name>:
        sshHost: <address used for ssh>
        ...            # extra fields from hostInfoFields
    groups:
      <group>: [<name>, ...]
"""

import logging
import os
import sys

import yaml

logger = logging.getLogger(__name__)


def load_inventory(cfg):
    """Load inventory from cfg['inventoryFilePath'], exit on failure."""
    path = os.path.expanduser(cfg['inventoryFilePath'])
    try:
        with open(path, 'r') as f:
            inventory = yaml.load(f, Loader=yaml.Loader)
    except Exception as e:
        logger.error("failed load inventory from file='%s', error='%s'", path, e)
        sys.exit(1)
    if not isinstance(inventory, dict):
        logger.error("inventory file='%s' is not a mapping", path)
        sys.exit(1)
    inventory.setdefault('hosts', {})
    inventory.setdefault('groups', {})
    return inventory


def resolve_ssh_host(host, inventory, inventory_path=None):
    """Return the address to ssh to for a single inventory host name.

    Falls back to the name itself (with a warning) when it is not in the inventory.
    """
    entry = inventory.get('hosts', {}).get(host)
    if entry is None:
        logger.warning("host='%s' not found in inventory file='%s', using it as is", host, inventory_path)
        return host
    ssh_host = entry.get('sshHost') if isinstance(entry, dict) else None
    if not ssh_host:
        logger.error("host='%s' has no 'sshHost' in inventory file='%s'", host, inventory_path)
        sys.exit(1)
    return ssh_host


def resolve_hosts(hosts_or_groups, inventory):
    """Expand group names into ssh addresses; plain names are passed through."""
    hosts = []
    for item in hosts_or_groups:
        group_hosts = inventory.get('groups', {}).get(item)
        if group_hosts:
            for host in group_hosts:
                hosts.append(inventory.get('hosts', {}).get(host, {}).get('sshHost', host))
        else:
            hosts.append(item)
    return hosts
