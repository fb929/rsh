from rsh.plugins import PLUGINS, AwsInventory, GceInventory, OvhInventory
from rsh.plugins.base import InventoryPlugin


def test_registry_keys_are_config_sections():
    assert set(PLUGINS) == {'awsInventory', 'gceInventory', 'ovhInventory'}
    for key, plugin in PLUGINS.items():
        assert plugin.config_key == key


class FakePlugin(InventoryPlugin):
    config_key = 'fakeInventory'
    hosting = 'fake'

    def __init__(self, cfg, records):
        super().__init__(cfg)
        self.records = records

    def fetch(self):
        return self.records


def test_normalize_adds_suffix_module_hosting_and_ssh_host():
    cfg = {'fakeInventory': {'nameSuffix': '.fk', 'sshHostField': 'ip', 'hostInfoFields': ['ip', 'dc']}}
    plugin = FakePlugin(cfg, [{'host': 'a', 'dc': 'x', 'ip': '1.1.1.1', 'tags': []}])
    [info] = plugin.instances_info()
    assert info['host'] == 'a.fk'
    assert info['rshInventoryModule'] == 'fakeInventory'  # config key, not the class name
    assert info['hosting'] == 'fake'
    assert info['sshHost'] == '1.1.1.1'


def test_normalize_defaults_missing_host_info_fields_and_tags():
    cfg = {'fakeInventory': {'hostInfoFields': ['missing']}}
    [info] = FakePlugin(cfg, [{'host': 'a', 'dc': 'x'}]).instances_info()
    assert info['missing'] == 'unknown'
    assert info['tags'] == []
    assert info['sshHost'] == 'a'  # sshHostField defaults to 'host'


def test_normalize_skips_records_without_host_and_deduplicates():
    cfg = {'fakeInventory': {}}
    records = [{'dc': 'x'}, {'host': 'a', 'dc': 'x'}, {'host': 'a', 'dc': 'x'}]
    assert len(FakePlugin(cfg, records).instances_info()) == 1


def test_aws_fetch_region(monkeypatch):
    cfg = {'awsInventory': {'skipNotRunningInstance': True, 'hostInfoFields': ['PrivateIpAddress'], 'nameSuffix': '.aws'}}
    plugin = AwsInventory(cfg)
    describe = {'Reservations': [{'Instances': [
        {'InstanceId': 'i-1', 'State': {'Name': 'running'}, 'Placement': {'AvailabilityZone': 'eu-1a'},
         'PrivateIpAddress': '10.0.0.1', 'Tags': [{'Key': 'Name', 'Value': 'web1'}, {'Key': 'role', 'Value': 'web'}]},
        {'InstanceId': 'i-2', 'State': {'Name': 'stopped'}, 'Placement': {'AvailabilityZone': 'eu-1a'}, 'Tags': [{'Key': 'Name', 'Value': 'off'}]},
        {'InstanceId': 'i-3', 'State': {'Name': 'running'}, 'Placement': {'AvailabilityZone': 'eu-1a'}, 'Tags': []},
    ]}]}
    monkeypatch.setattr(plugin, 'run_cmd', lambda command, parse_json=True: describe)
    [record] = list(plugin.fetch_region('eu-1'))
    assert record == {'host': 'web1', 'dc': 'eu-1a', 'PrivateIpAddress': '10.0.0.1',
                      'tags': [{'Key': 'Name', 'Value': 'web1'}, {'Key': 'role', 'Value': 'web'}]}
    info = plugin.normalize(record)
    assert info['host'] == 'web1.aws' and info['sshHost'] == 'web1.aws'


def test_gce_fetch_handles_missing_external_ip_and_filters_tags(monkeypatch):
    cfg = {'gceInventory': {'skipNotRunningInstance': True}}
    plugin = GceInventory(cfg)
    instances = [
        {'name': 'ctl', 'status': 'RUNNING', 'zone': 'projects/x/zones/eu-west4-c',
         'networkInterfaces': [{'networkIP': '10.0.0.5'}],
         'metadata': {'items': [{'key': 'managed_by', 'value': 'puppet'}, {'key': 'startup-script', 'value': '#!/bin/sh'},
                                {'key': 'weird key', 'value': 'x'}]}},
        {'name': 'gone', 'status': 'TERMINATED', 'zone': 'z', 'networkInterfaces': [{'networkIP': '10.0.0.9'}]},
    ]
    monkeypatch.setattr(plugin, 'run_cmd', lambda command, parse_json=True: instances)
    [record] = list(plugin.fetch())
    assert record['dc'] == 'eu-west4-c'
    assert record['PublicIpAddress'] == 'unknown'
    assert record['tags'] == [{'Key': 'managed_by', 'Value': 'puppet'}]


def test_ovh_ssh_host_field_outside_host_info_fields():
    cfg = {'ovhInventory': {'sshHostField': 'internalName', 'hostInfoFields': ['publicIp']}}
    plugin = OvhInventory(cfg)
    plugin.fetch = lambda: [{'host': 'srv', 'customName': 'srv', 'publicIp': '5.5.5.5', 'internalName': 'ns1.eu', 'dc': 'rbx', 'tags': []}]
    [info] = plugin.instances_info()
    assert info['sshHost'] == 'ns1.eu'
