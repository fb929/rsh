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
    'awsInventory': {
        'regions': [],
        'sshHostField': 'PrivateIpAddress', # field for 'sshHost' in aws data, variants: PublicDnsName, PublicIpAddress, PrivateDnsName, PrivateIpAddress
        'skipTagsForMakeGroups': [ # these tag 'key' will skip when creating groups
            'Name',
            'Description',
            'description',
        ],
        'skipNotRunningInstance': True, # skipping not running instance
    },
    'sr': {
        'ssh': {
            'command': 'ssh -Y -o ConnectTimeout=5 -o StrictHostKeyChecking=no',
        },
        'pexpect': {
            'timeout': 120,
        },
        'useInventorySshHost': True, # use sshHost from inventory for connect to host
        'escalatePrivilegesCommand': 'su -m', # variants: 'su -m', 'sudo -s'
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
# }}
