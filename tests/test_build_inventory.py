from rsh.build_inventory import build_inventory, natural_sort_key, collect_records


def test_natural_sort_key_orders_numbers_numerically_and_ignores_domain():
    names = ['web10.aws', 'web2.aws', 'web1', 'db1']
    assert sorted(names, key=natural_sort_key) == ['db1', 'web1', 'web2.aws', 'web10.aws']


def test_build_inventory_hosts_groups_and_skips():
    cfg = {
        'awsInventory': {'hostInfoFields': ['PrivateIpAddress'], 'skipTagsForMakeGroups': ['Name']},
    }
    records = [
        {'host': 'web10', 'dc': 'eu-1a', 'sshHost': '10.0.0.10', 'PrivateIpAddress': '10.0.0.10',
         'rshInventoryModule': 'awsInventory', 'hosting': 'aws',
         'tags': [{'Key': 'Name', 'Value': 'web10'}, {'Key': 'role', 'Value': 'web'}]},
        {'host': 'web2', 'dc': 'eu-1a', 'sshHost': '10.0.0.2', 'PrivateIpAddress': '10.0.0.2',
         'rshInventoryModule': 'awsInventory', 'hosting': 'aws',
         'tags': [{'Key': 'role', 'Value': 'web'}, {'Key': 'has space', 'Value': 'a-b'}]},
    ]
    inventory = build_inventory(records, cfg)
    assert list(inventory['hosts']) == ['web2', 'web10']
    assert inventory['hosts']['web10'] == {'sshHost': '10.0.0.10', 'PrivateIpAddress': '10.0.0.10'}
    assert inventory['groups']['tag_role_web'] == ['web2', 'web10']
    assert inventory['groups']['dc_aws_eu_1a'] == ['web2', 'web10']
    assert 'tag_Name_web10' not in inventory['groups']
    assert inventory['groups']['tag_has_space_a_b'] == ['web2']


def test_collect_records_runs_only_enabled_plugins(monkeypatch):
    calls = []

    class Stub:
        def __init__(self, cfg):
            pass

        def instances_info(self):
            calls.append('run')
            return [{'host': 'x'}]

    monkeypatch.setattr('rsh.build_inventory.PLUGINS', {'stubInventory': Stub, 'otherInventory': Stub})
    cfg = {'stubInventory': {'enable': True}, 'otherInventory': {'enable': False}, 'unknownInventory': {'enable': True}}
    assert collect_records(cfg) == [{'host': 'x'}]
    assert calls == ['run']
