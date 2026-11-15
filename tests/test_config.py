import logging

from rsh import config


def test_parse_log_level():
    assert config.parse_log_level('warn') == logging.WARNING
    assert config.parse_log_level('WARNING') == logging.WARNING
    assert config.parse_log_level('debug') == logging.DEBUG
    assert config.parse_log_level('info') == logging.INFO
    assert config.parse_log_level('nonsense') == logging.INFO


def test_find_values_walks_dicts_and_lists():
    data = {'a': {'application_key': 'K1', 'x': [{'consumer_key': 'K2'}, 'noise']}, 'consumer_key': 'K3'}
    assert sorted(config.find_values(data, ['application_key', 'consumer_key'])) == ['K1', 'K2', 'K3']
    assert config.find_values(data, 'application_key') == ['K1']


def test_sensitive_formatter_masks_values():
    formatter = config.SensitiveFormatter('%(message)s', None, ['s3cr3t', 'a+b', None, ''])
    record = logging.LogRecord('t', logging.INFO, __file__, 1, 'key s3cr3t and a+b here', None, None)
    assert formatter.format(record) == 'key [CLASSIFIED] and [CLASSIFIED] here'


def test_sensitive_formatter_without_values_is_passthrough():
    formatter = config.SensitiveFormatter('%(message)s', None, [])
    record = logging.LogRecord('t', logging.INFO, __file__, 1, 'plain', None, None)
    assert formatter.format(record) == 'plain'


def test_load_config_files_merges_and_skips_bad_files(tmp_path):
    good = tmp_path / 'good.yaml'
    good.write_text('sr:\n  escalatePrivilegesCommands:\n    - su -m\n')
    bad = tmp_path / 'bad.yaml'
    bad.write_text('- not\n- a mapping\n')
    cfg = config.load_config_files({'sr': {'escalatePrivilegesCommands': [], 'other': 1}}, [str(good), str(bad), str(tmp_path / 'missing.yaml')])
    assert cfg['sr']['escalatePrivilegesCommands'] == ['su -m']
    assert cfg['sr']['other'] == 1
