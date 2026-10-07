# -*- coding: utf-8 -*-
"""OVH dedicated servers inventory plugin (uses the ovh API SDK)."""

import json

from .base import InventoryPlugin


class OvhInventory(InventoryPlugin):
    config_key = 'ovhInventory'
    hosting = 'ovh'

    def client(self):
        import ovh  # imported lazily so the SDK is only required when the plugin is enabled
        api = self.settings['api']
        return ovh.Client(
            endpoint=api['endpoint'],
            application_key=api['application_key'],
            application_secret=api['application_secret'],
            consumer_key=api['consumer_key'],
        )

    def fetch(self):
        client = self.client()
        for server in client.get('/dedicated/server'):
            service = client.get('/dedicated/server/%s/serviceInfos' % server)
            service_info = client.get('/services/%s' % service['serviceId'])
            self.logger.debug("service_info=%s", json.dumps(service_info, indent=4))
            server_info = client.get('/dedicated/server/%s' % server)
            self.logger.debug("server_info=%s", json.dumps(server_info, indent=4))
            dc = server_info.get('availabilityZone')
            if not dc or dc == 'unknown':
                dc = server_info.get('datacenter', 'unknown')
            yield {
                'host': service_info['resource']['displayName'],
                'customName': service_info['resource']['displayName'],
                'publicIp': server_info.get('ip', 'unknown'),
                'internalName': server_info.get('name', 'unknown'),
                'dc': dc,
                'tags': [],  # ovh has no tags
            }
