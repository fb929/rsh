# -*- coding: utf-8 -*-
"""Google Compute Engine inventory plugin (uses the gcloud cli)."""

import re

from .base import InventoryPlugin

SIMPLE_VALUE = re.compile(r"[A-Za-z0-9_-]+")


class GceInventory(InventoryPlugin):
    config_key = 'gceInventory'
    hosting = 'gce'

    def fetch(self):
        for instance in self.run_cmd("gcloud compute instances list --format=json"):
            name = instance['name']
            if self.settings.get('skipNotRunningInstance') and instance.get('status') != 'RUNNING':
                self.logger.debug("skipping instance name='%s', status='%s'", name, instance.get('status'))
                continue
            interface = instance['networkInterfaces'][0]
            # an instance without external IP has no accessConfigs / natIP
            access_configs = interface.get('accessConfigs') or [{}]
            yield {
                'host': name,
                'dc': instance['zone'].split('/')[-1],
                'PrivateIpAddress': interface['networkIP'],
                'PublicIpAddress': access_configs[0].get('natIP', 'unknown'),
                'tags': self.tags(instance),
            }

    def tags(self, instance):
        """Metadata items with simple key/value become tags; startup-script and the like are skipped."""
        tags = []
        for item in instance.get('metadata', {}).get('items', []):
            key, value = item.get('key', ''), str(item.get('value', ''))
            if key == 'startup-script':
                continue
            if not SIMPLE_VALUE.fullmatch(key) or not SIMPLE_VALUE.fullmatch(value):
                self.logger.debug("skipping metadata key='%s': not a simple key/value", key)
                continue
            tags.append({'Key': key, 'Value': value})
        return tags
