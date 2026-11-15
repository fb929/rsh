import pytest

from rsh import sr


def test_find_root_password_first_match_wins():
    data = '# comment\n\nbad line without tab\n^web.*\tsecret1\n.*\tfallback'
    assert sr.find_root_password(data, 'web7') == 'secret1'
    assert sr.find_root_password(data, 'db1') == 'fallback'


def test_find_root_password_is_case_insensitive():
    assert sr.find_root_password('^WEB\tpw', 'web1') == 'pw'


def test_find_root_password_no_match():
    assert sr.find_root_password('^db\tx', 'web1') is None


def test_find_root_password_keeps_tabs_inside_password():
    assert sr.find_root_password('.*\tpass\twith\ttabs', 'h') == 'pass\twith\ttabs'


def test_get_escalate_commands_list():
    cfg = {'sr': {'escalatePrivilegesCommands': ['su -m', 'sudo -s -E']}}
    assert sr.get_escalate_commands(cfg) == ['su -m', 'sudo -s -E']


def test_get_escalate_commands_string_is_wrapped():
    assert sr.get_escalate_commands({'sr': {'escalatePrivilegesCommands': 'su -m'}}) == ['su -m']


def test_get_escalate_commands_legacy_fallback():
    cfg = {'sr': {'escalatePrivilegesCommands': [], 'escalatePrivilegesCommand': 'sudo -s'}}
    assert sr.get_escalate_commands(cfg) == ['sudo -s']


def test_get_escalate_commands_empty_exits():
    with pytest.raises(SystemExit):
        sr.get_escalate_commands({'sr': {'escalatePrivilegesCommands': [], 'escalatePrivilegesCommand': None}})


def test_parse_args_inventory_flags_are_exclusive():
    with pytest.raises(SystemExit):
        sr.parse_args(['--forceUseInventory', '--forceDontUseInventory', 'host'])
    assert sr.parse_args(['--forceDontUseInventory', 'host']).forceDontUseInventory is True
