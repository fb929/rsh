# rsh
scripts for auto login and parallel/successively execute command on linux servers

## description
* sr - server root
  login over ssh and escalate privileges
* sExec - successively execute command on servers list or group
* pExec - parallel execute command on servers list or group

## install
```
pip install rsh-tools
```
installs the commands `sr`, `sExec`, `pExec`, `rshInventory` and `rshCompgen`.
with the OVH inventory plugin: `pip install 'rsh-tools[ovh]'`

bash completion for hosts and groups — add to `~/.bashrc`:
```
eval "$(rshCompgen completion)"
```

### development
```
git clone https://github.com/fb929/rsh && cd rsh
make dev     # pip install --editable '.[dev,ovh]'
make test    # pytest
```
the editable install puts the real commands on PATH, so the checkout is what runs.

### release
bump `__version__` in `rsh/__init__.py` ([semver](https://semver.org)), then tag and push:
```
git tag v3.0.0 && git push origin v3.0.0
```
the release workflow checks that the tag matches `__version__`, builds sdist + wheel,
uploads them to PyPI (secret `PYPI_API_TOKEN`) and attaches them to the GitHub release.

## configure
### (optional) passwords file for "su" mode
* create encrypt file .pass.gpg
* add passwords in format:
  ```
  <hostname regex>\t<root password>
  ```

  example
  ```
  .*	myRootPasswd
  ```
* configure ~/.rsh.yaml
  ```
  sr:
    escalatePrivilegesCommands:
      - 'su -m'
      - 'sudo -s -E'
  ```
  commands are tried on the host in the listed order; the first one that gives a root shell wins,
  if none of them succeeds `sr` exits with an error.
  the old single-value option `escalatePrivilegesCommand` still works, but is used only when `escalatePrivilegesCommands` is empty

### aws inventory plugin
* install package [aws-cli](https://github.com/aws/aws-cli)
* configure ~/.aws/credentials

### ovh inventory plugin
* `pip install 'rsh-tools[ovh]'`
* configure ~/.rsh.yaml
  ```
  ovhInventory:
    api:
      endpoint: ovh-ca
      application_key: xxx
      application_secret: yyy
      consumer_key: xxx
  ```
  [create api tokens](https://help.ovhcloud.com/csm/en-api-getting-started-ovhcloud-api?id=kb_article_view&sysparm_article=KB0042777)

### gce inventory plugin
* install add setup [gcloud cli](https://cloud.google.com/sdk/docs/install)

### all configuration options
see the defaults in [rsh/config.py](rsh/config.py); `~/.rsh.yaml` (and `/etc/rsh/config.yaml`, `./.config.yaml`) are deep-merged over them
