# -*- coding: utf-8 -*-
"""AWS EC2 inventory plugin (uses the aws cli)."""

from .base import InventoryPlugin


class AwsInventory(InventoryPlugin):
    config_key = 'awsInventory'
    hosting = 'aws'

    def regions(self):
        configured = self.settings.get('regions')
        if configured:
            return configured
        return self.run_cmd("aws ec2 describe-regions --query 'Regions[].RegionName'")

    def fetch(self):
        regions = self.regions()
        self.logger.debug("regions=%s", regions)
        for region in regions:
            yield from self.fetch_region(region)

    def fetch_region(self, region):
        describe = self.run_cmd("aws ec2 --region %s describe-instances" % region)
        for reservation in describe.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                if self.settings.get('skipNotRunningInstance') and instance.get('State', {}).get('Name') != 'running':
                    continue
                tags = instance.get('Tags', [])  # tags are optional
                name = next((tag['Value'] for tag in tags if tag.get('Key') == 'Name'), None)
                if not name:
                    self.logger.warning("skipping instance id='%s' without 'Name' tag", instance.get('InstanceId'))
                    continue
                try:
                    dc = instance['Placement']['AvailabilityZone']
                except KeyError:
                    self.logger.warning("skipping instance id='%s' without Placement.AvailabilityZone", instance.get('InstanceId'))
                    continue
                record = {
                    'host': name,
                    'dc': dc,
                    'tags': tags,
                }
                for field in self.settings.get('hostInfoFields', []):
                    record[field] = instance.get(field, 'unknown')
                yield record
