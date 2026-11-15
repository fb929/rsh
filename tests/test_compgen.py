from rsh import compgen


def test_completion_script_is_shipped():
    script = compgen.completion_script()
    assert 'complete -F _rsh_completion_hosts sr' in script
    assert 'rshCompgen hosts' in script


def test_main_prints_hosts_and_groups(tmp_path, capsys, monkeypatch):
    path = tmp_path / 'inventory.yaml'
    path.write_text('hosts: {b: {sshHost: x}, a: {sshHost: y}}\ngroups: {g1: [a]}\n')
    monkeypatch.setitem(compgen.rsh.config.cfg, 'inventoryFilePath', str(path))
    compgen.main(['hosts'])
    compgen.main(['groups'])
    assert capsys.readouterr().out == 'b a\ng1\n'
