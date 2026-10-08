#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from os.path import expanduser
import sys
import yaml
import re
import logging
from deepmerge import always_merger

PROGRAM_NAME = 'rsh'
HOME_DIR = expanduser("~")
DEFAULT_CONFIG_FILES = [
    '/etc/' + PROGRAM_NAME + '/config.yaml',
    HOME_DIR + '/.' + PROGRAM_NAME + '.yaml',
    './.config.yaml',
]
cfg = {
    #'logFile': HOME_DIR + '/log/' + PROGRAM_NAME + '/' + PROGRAM_NAME + '.log',
    'logFile': 'stdout',
    'logLevel': 'info',
    'gpgFile': HOME_DIR + '/.pass.gpg',
    'inventoryFilePath': HOME_DIR + '/inventory.yaml',
    'sensitiveKeys': [
        'application_key',
        'application_secret',
        'consumer_key',
    ],
    'awsInventory': {
        'enable': True,
        'regions': [],
        'sshHostField': 'host',             # field for 'sshHost', variants: host, PublicDnsName, PublicIpAddress, PrivateDnsName, PrivateIpAddress
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
        'nameSuffix': '.aws',               # suffix for instance names
    },
    'ovhInventory': {
        'enable': True,
        'api': {
            'endpoint': 'ovh-ca',           # Endpoint of API OVH
            'application_key': 'xxx',       # Application Key
            'application_secret': 'yyy',    # Application Secret
            'consumer_key': 'zzz',          # Consumer Key
        },
        'sshHostField': 'host',             # field for 'sshHost', variants: host, customName, publicIp, internalName
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
        'sshHostField': 'host',             # field for 'sshHost', variants: host, PrivateIpAddress, PublicIpAddress
        'hostInfoFields': [
            'PrivateIpAddress',
            'PublicIpAddress',
            'dc',
        ],
        'skipTagsForMakeGroups': [          # these tag 'key' will skip when creating groups
            'name',
        ],
        'nameSuffix': '.gc',               # suffix for instance names
    },
    'sr': {
        'ssh': {
            'command': 'ssh -Y -o ConnectTimeout=5 -o StrictHostKeyChecking=no',
        },
        'pexpect': {
            'timeout': 120,
        },
        'useInventorySshHost': True, # use sshHost from inventory for connect to host
        'escalatePrivilegesCommands': [],   # commands are tried on the host in the listed order until one gives a root shell,
                                            # e.g. ['su -m', 'sudo -s -E'];
                                            # must stay empty here: deepmerge appends lists, so a default value would be added to the user's list
        'escalatePrivilegesCommand': 'sudo -s -E', # deprecated, used only when 'escalatePrivilegesCommands' is empty; variants: 'su -m', 'sudo -s', 'sudo -s -E'
        'postLoginCommand': None # command will run after login, used to set up the environment
    },
}

# load config files {{
def load_config_files(cfg, paths):
    """Deep-merge every existing YAML mapping from paths into cfg, in order."""
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r') as f:
                loaded = yaml.load(f, Loader=yaml.Loader)
        except Exception as e:
            logging.warning("skipping config file '%s': %s", path, e)
            continue
        if not isinstance(loaded, dict):
            logging.warning("skipping config file '%s': top level is not a mapping", path)
            continue
        cfg = always_merger.merge(cfg, loaded)
    return cfg

cfg = load_config_files(cfg, DEFAULT_CONFIG_FILES)
cfg['logDir'] = os.path.dirname(cfg['logFile']) or '.'
# }}

# logging {{
def parse_log_level(name):
    if re.match(r"^(warn|warning)$", str(name), re.IGNORECASE):
        return logging.WARNING
    if re.match(r"^debug$", str(name), re.IGNORECASE):
        return logging.DEBUG
    return logging.INFO


def find_values(data, keys):
    """Collect values of the given keys anywhere in a nested dict/list structure."""
    if isinstance(keys, str):
        keys = [keys]
    found = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys:
                found.append(value)
            else:
                found.extend(find_values(value, keys))
    elif isinstance(data, list):
        for item in data:
            found.extend(find_values(item, keys))
    return found


class SensitiveFormatter(logging.Formatter):
    """Masks sensitive config values (api keys etc.) in log output."""

    def __init__(self, fmt, datefmt, sensitive_values):
        super().__init__(fmt, datefmt=datefmt)
        values = [str(value) for value in sensitive_values if value]
        self.pattern = re.compile('|'.join(re.escape(value) for value in values)) if values else None

    def format(self, record):
        message = super().format(record)
        if self.pattern is None:
            return message
        return self.pattern.sub('[CLASSIFIED]', message)


LOG_FORMAT = '%(asctime)s\t%(name)s\t%(funcName)s\t%(levelname)s\t%(message)s'
LOG_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'


def setup_logging(cfg):
    level = parse_log_level(cfg['logLevel'])
    if level > logging.DEBUG:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
    if cfg['logFile'] == 'stdout':
        logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    else:
        os.makedirs(cfg['logDir'], exist_ok=True)
        logging.basicConfig(filename=cfg['logFile'], level=level, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    formatter = SensitiveFormatter(LOG_FORMAT, LOG_DATE_FORMAT, find_values(cfg, cfg['sensitiveKeys']))
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)

setup_logging(cfg)
# }}
