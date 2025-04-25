#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from os.path import expanduser
import sys
import yaml
import re
import logging
import inspect
from deepmerge import always_merger

programName = 'rsh'
homeDir = expanduser("~")
defaultConfigFiles = [
    '/etc/' + programName + '/config.yaml',
    homeDir + '/.' + programName + '.yaml',
    './.config.yaml',
]
cfg = {
    #'logFile': homeDir + '/log/' + programName + '/' + programName + '.log',
    'logFile': 'stdout',
    'logLevel': 'info',
    'gpgFile': homeDir + '/.pass.gpg',
    'inventoryFilePath': homeDir + '/inventory.yaml',
    'sensitiveKeys': [
        'application_key',
        'application_secret',
        'consumer_key',
    ],
    'awsInventory': {
        'enable': True,
        'regions': [],
        'sshHostField': 'PrivateIpAddress', # field for 'sshHost' in aws data, variants: PublicDnsName, PublicIpAddress, PrivateDnsName, PrivateIpAddress
        'skipTagsForMakeGroups': [          # these tag 'key' will skip when creating groups
            'Name',
            'Description',
            'description',
        ],
        'skipNotRunningInstance': True,     # skipping not running instance
        'hostInfoFields': [
            'PrivateIpAddress',
            'PublicIpAddress',
        ],
    },
    'ovhInventory': {
        'enable': True,
        'api': {
            'endpoint': 'ovh-ca',           # Endpoint of API OVH
            'application_key': 'xxx',       # Application Key
            'application_secret': 'yyy',    # Application Secret
            'consumer_key': 'zzz',          # Consumer Key
        },
        'sshHostField': 'customName',       # field for 'sshHost' in ovh data, variants: customName, publicIp, internalName
        'skipTagsForMakeGroups': [],        # these tag 'key' will skip when creating groups
        'hostInfoFields': [
            'publicIp',
            'internalName', # internal name
            'dc',
        ],
    },
    'gceInventory': {
        'enable': True,
        'skipNotRunningInstance': True,     # skipping not running instance
        'sshHostField': 'PrivateIpAddress',
        'hostInfoFields': [
            'PrivateIpAddress',
            'PublicIpAddress',
            'dc',
        ],
        'skipTagsForMakeGroups': [],        # these tag 'key' will skip when creating groups
        'nameSuffix': '.gc',                # suffix for instance names
    },
    'sr': {
        'ssh': {
            'command': 'ssh -Y -o ConnectTimeout=5 -o StrictHostKeyChecking=no',
        },
        'pexpect': {
            'timeout': 120,
        },
        'useInventorySshHost': True, # use sshHost from inventory for connect to host
        'escalatePrivilegesCommand': 'sudo -s', # variants: 'su -m', 'sudo -s'
        'postLoginCommand': None # command will run after login, used to set up the environment
    },
}

# get settings
for configFile in defaultConfigFiles:
    if os.path.isfile(configFile):
        try:
            with open(configFile, 'r') as ymlfile:
                try:
                    cfg = always_merger.merge(cfg,yaml.load(ymlfile,Loader=yaml.Loader))
                except Exception as e:
                    logging.warning("main: skipping load load config file: '%s', error '%s'", configFile, e)
                    continue
        except:
            continue

# fix logDir
cfg['logDir'] = os.path.dirname(cfg['logFile'])
if cfg['logDir'] == '':
    cfg['logDir'] = '.'
# }}

# basic config {{
for dirPath in [
    cfg['logDir'],
]:
    try:
        os.makedirs(dirPath)
    except OSError:
        if not os.path.isdir(dirPath):
            raise

# choice logLevel
if re.match(r"^(warn|warning)$", cfg['logLevel'], re.IGNORECASE):
    logLevel = logging.WARNING
elif re.match(r"^debug$", cfg['logLevel'], re.IGNORECASE):
    logLevel = logging.DEBUG
else:
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logLevel = logging.INFO
# }}

# sensitive data {{
def getRecursively(searchDict,fields):
    """
    Takes a dict with nested lists and dicts,
    and searches all dicts for a key of the field
    provided.
    """
    if isinstance(fields, str):
        fields = [fields]
    fieldsFound = []
    for field in fields:
        for key, value in searchDict.items():
            if key == field:
                fieldsFound.append(value)
            elif isinstance(value, dict):
                results = getRecursively(value, field)
                for result in results:
                    fieldsFound.append(result)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        more_results = getRecursively(item, field)
                        for another_result in more_results:
                            fieldsFound.append(another_result)
    return fieldsFound
sensitiveValues = getRecursively(cfg, cfg['sensitiveKeys'])
class SensitiveFormatter(logging.Formatter):
    """Formatter that removes sensitive information in urls."""
    @staticmethod
    def _filter(s):
        pattern = re.compile('|'.join(sensitiveValues))
        return pattern.sub('[CLASSIFIED]', s)

    def format(self, record):
        original = logging.Formatter.format(self, record)
        return self._filter(original)
# }}

# configure log format {{
if cfg['logFile'] == 'stdout':
    logging.basicConfig(
        level       = logLevel,
        format      = '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
        datefmt     = '%Y-%m-%dT%H:%M:%S',
    )
else:
    logging.basicConfig(
        filename    = cfg['logFile'],
        level       = logLevel,
        format      = '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
        datefmt     = '%Y-%m-%dT%H:%M:%S',
    )
for handler in logging.root.handlers:
   handler.setFormatter(SensitiveFormatter('%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'))
# }}
