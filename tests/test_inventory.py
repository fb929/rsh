import pytest

from rsh.inventory import load_inventory, resolve_hosts, resolve_ssh_host

INVENTORY = {
    'hosts': {
        'web1': {'sshHost': '10.0.0.1'},
        'web2': {'sshHost': '10.0.0.2'},
        'broken': {},
    },
    'groups': {'web': ['web1', 'web2', 'ghost']},
}


def test_resolve_ssh_host_known():
    assert resolve_ssh_host('web1', INVENTORY) == '10.0.0.1'


def test_resolve_ssh_host_unknown_falls_back_to_name():
    assert resolve_ssh_host('nothere', INVENTORY) == 'nothere'


def test_resolve_ssh_host_without_ssh_host_exits():
    with pytest.raises(SystemExit):
        resolve_ssh_host('broken', INVENTORY)


def test_resolve_hosts_expands_groups_and_passes_names_through():
    assert resolve_hosts(['web', 'db9'], INVENTORY) == ['10.0.0.1', '10.0.0.2', 'ghost', 'db9']


def test_load_inventory(tmp_path):
    path = tmp_path / 'inventory.yaml'
    path.write_text('hosts:\n  a:\n    sshHost: 1.1.1.1\n')
    inventory = load_inventory({'inventoryFilePath': str(path)})
    assert inventory['hosts']['a']['sshHost'] == '1.1.1.1'
    assert inventory['groups'] == {}


def test_load_inventory_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit):
        load_inventory({'inventoryFilePath': str(tmp_path / 'missing.yaml')})


def test_load_inventory_not_a_mapping_exits(tmp_path):
    path = tmp_path / 'inventory.yaml'
    path.write_text('- just\n- a list\n')
    with pytest.raises(SystemExit):
        load_inventory({'inventoryFilePath': str(path)})
