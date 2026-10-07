# -*- coding: utf-8 -*-
"""Base class for inventory plugins.

A plugin fetches raw host records from one provider; the base class turns them
into the uniform shape rshInventory expects:

    {
        "host":               <inventory name, nameSuffix applied>,
        "dc":                 <datacenter / zone>,
        "tags":               [{"Key": ..., "Value": ...}, ...],
        "sshHost":            <value of the field named by sshHostField>,
        "rshInventoryModule": <config key, e.g. "awsInventory">,
        "hosting":            <provider short name>,
        ...                   <provider fields, at least those in hostInfoFields>
    }

'rshInventoryModule' is written to inventory.yaml and later used as a config key,
so it must stay equal to the plugin's config section name, not its class name.
"""

import json
import logging
import subprocess
import sys


def run_cmd(command, parse_json=True, logger=None):
    """Run a shell command, return its stdout (parsed as JSON by default) or None on failure."""
    logger = logger or logging.getLogger(__name__)
    logger.debug("run '%s'", command)
    try:
        completed = subprocess.run(['bash', '-c', command], capture_output=True, text=True)
    except OSError as e:
        logger.error("failed run '%s', error='%s'", command, e)
        return None
    stdout = completed.stdout.rstrip()
    if completed.returncode != 0:
        logger.error("command '%s' exited with %d, stderr='%s'", command, completed.returncode, completed.stderr.rstrip())
        return None
    if not parse_json:
        return stdout
    try:
        return json.loads(stdout)
    except ValueError as e:
        logger.error("failed parse JSON from '%s', error='%s', stderr='%s'", command, e, completed.stderr.rstrip())
        return None


class InventoryPlugin:
    """Subclasses set config_key and hosting and implement fetch()."""

    config_key = None   # config section, e.g. 'awsInventory'; also the rshInventoryModule value
    hosting = None      # short provider name, used for dc_<hosting>_<dc> groups

    def __init__(self, cfg):
        self.cfg = cfg
        self.settings = cfg.get(self.config_key) or {}
        self.logger = logging.getLogger('rsh.plugins.%s' % self.config_key)

    def fetch(self):
        """Return an iterable of raw records: dicts with at least 'host', 'dc' and 'tags'."""
        raise NotImplementedError

    def run_cmd(self, command, parse_json=True):
        result = run_cmd(command, parse_json=parse_json, logger=self.logger)
        if result is None:
            sys.exit(1)
        return result

    def instances_info(self):
        records = []
        for raw in self.fetch():
            info = self.normalize(raw)
            if info is not None and info not in records:
                records.append(info)
        return records

    def normalize(self, raw):
        info = dict(raw)
        host = info.get('host')
        if not host:
            self.logger.warning("skipping record without 'host': %s", raw)
            return None
        suffix = self.settings.get('nameSuffix')
        if suffix:
            info['host'] = host + suffix
        info.setdefault('tags', [])
        info['rshInventoryModule'] = self.config_key
        info['hosting'] = self.hosting
        for field in self.settings.get('hostInfoFields', []):
            info.setdefault(field, 'unknown')
        info['sshHost'] = info.get(self.settings.get('sshHostField', 'host'), 'unknown')
        return info
