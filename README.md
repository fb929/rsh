# rsh
scripts for auto login and parallel/successively execute command on linux servers

## description
* sr - server root
  login over ssh and escalate privileges
* TODO sExec - successively execute command on servers list or group
* TODO pExec - parallel execute command on servers list or group

## install
pip install --user --requirement ./requirements.txt

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
    escalatePrivilegesCommand: 'su -m'
  ```

### aws inventory plugin
* install package [aws-cli](https://github.com/aws/aws-cli)
* configure ~/.aws/credentials

### ovh inventory plugin
* install pip module ovh
* configre ~/.rsh.yaml
  ```
  ovhInventory:
    api:
      endpoint: ovh-ca
      application_key: xxx
      application_secret: yyy
      consumer_key: xxx
  ```
  [create api tokens](https://help.ovhcloud.com/csm/en-api-getting-started-ovhcloud-api?id=kb_article_view&sysparm_article=KB0042777)

### all configuration options https://github.com/fb929/rsh/blob/main/rsh/config.py#L20
