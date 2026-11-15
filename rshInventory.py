#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rshInventory - collect hosts from the enabled inventory plugins and write inventory.yaml."""

import os
import sys
# make the package next to this script win over any stale install (e.g. /opt/rsh),
# resolving symlinks so launching via a symlink in PATH still finds it
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
sys.path.append('/opt/rsh')
import json
import logging
import re

import yaml

import rsh.config
from rsh.plugins import PLUGINS

logger = logging.getLogger('rshInventory')


def natural_sort_key(name):
    """Token-aware natural order: 'web2' < 'web10'; the domain part (e.g. '.aws') is ignored."""
    left = str(name).split('.', 1)[0]
    tokens = []
    for rough in re.split(r'[^A-Za-z0-9]+', left):
        for part in re.findall(r'[A-Za-z]+|\d+', rough):
            tokens.append((1, int(part)) if part.isdigit() else (0, part.lower()))
    return tokens


def group_name(*parts):
    name = '_'.join(part.replace('-', '_') for part in parts)
    return re.sub(r'\s+', '_', name)


def collect_records(cfg):
    """Run every enabled plugin, return the merged list of normalized records."""
    records = []
    for key, plugin_class in PLUGINS.items():
        if not (cfg.get(key) or {}).get('enable'):
            logger.debug("plugin '%s' disabled", key)
            continue
        logger.debug("running plugin '%s'", key)
        records.extend(plugin_class(cfg).instances_info())
    for key in cfg:
        if key.endswith('Inventory') and key not in PLUGINS:
            logger.warning("config section '%s' has no matching inventory plugin, known: %s", key, sorted(PLUGINS))
    return records


def build_inventory(records, cfg):
    """Turn plugin records into the {'hosts': ..., 'groups': ...} structure."""
    hosts = {}
    groups = {}

    def add_to_group(name, host):
        groups.setdefault(name, [])
        if host not in groups[name]:
            groups[name].append(host)

    for record in records:
        host = record.get('host')
        if not host:
            logger.error("record without 'host': %s", record)
            sys.exit(1)
        module = record.get('rshInventoryModule')
        settings = cfg.get(module) or {}
        if host not in hosts:
            hosts[host] = {'sshHost': record['sshHost']}
            for field in settings.get('hostInfoFields', []):
                hosts[host][field] = record.get(field, 'unknown')
        skip_tags = settings.get('skipTagsForMakeGroups', [])
        for tag in record.get('tags', []):
            if tag['Key'] in skip_tags:
                continue
            add_to_group(group_name('tag', tag['Key'], tag['Value']), host)
        add_to_group(group_name('dc', record.get('hosting', 'unknown'), record['dc']), host)

    hosts = {name: hosts[name] for name in sorted(hosts, key=natural_sort_key)}
    groups = {name: sorted(groups[name], key=natural_sort_key) for name in sorted(groups, key=natural_sort_key)}
    return {'hosts': hosts, 'groups': groups}


def write_inventory(inventory, path):
    path = os.path.expanduser(path)
    with open(path, 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False, sort_keys=False)
    logger.info("inventory written to '%s': %d hosts, %d groups", path, len(inventory['hosts']), len(inventory['groups']))


def main():
    cfg = rsh.config.cfg
    logger.debug("cfg=%s", json.dumps(cfg, indent=4))
    records = collect_records(cfg)
    logger.debug("records=%s", json.dumps(records, indent=4))
    inventory = build_inventory(records, cfg)
    logger.debug("inventory=%s", inventory)
    write_inventory(inventory, cfg['inventoryFilePath'])


if __name__ == "__main__":
    main()
