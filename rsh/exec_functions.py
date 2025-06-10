# exec_functions.py

import sys
import os
import yaml
import json
import argparse
from braceexpand import braceexpand
import rsh.config
import logging

logging.getLogger("paramiko").setLevel(logging.WARNING)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Execute commands via SSH on remote servers.',
        usage="[sExec|pExec] -g GROUP -c COMMAND or [sExec|pExec] GROUP COMMAND..."
    )
    parser.add_argument('-g', '--groups', dest='hosts_or_groups', nargs='+', help='Hosts or groups (supports brace expansions)')
    parser.add_argument('-c', '--command', nargs=argparse.REMAINDER, help='Command to execute')
    parser.add_argument('fallback', nargs=argparse.REMAINDER, help='Fallback: GROUP COMMAND ...')
    args = parser.parse_args()

    if args.hosts_or_groups and args.command:
        hosts_or_groups_raw, command_parts = args.hosts_or_groups, args.command
    elif args.fallback:
        hosts_or_groups_raw, command_parts = args.fallback[0], args.fallback[1:]
    else:
        parser.print_usage()
        sys.exit(1)

    hosts_or_groups = list(braceexpand(hosts_or_groups_raw)) if isinstance(hosts_or_groups_raw, str) else sum([list(braceexpand(x)) for x in hosts_or_groups_raw], [])
    return hosts_or_groups, ' '.join(command_parts)

def load_inventory():
    try:
        with open(os.path.expanduser(rsh.config.cfg['inventoryFilePath']), 'r') as f:
            return yaml.load(f, Loader=yaml.Loader)
    except Exception as e:
        rsh.config.logging.error(f"Failed to load inventory: {e}")
        sys.exit(1)

def resolve_hosts(hosts_or_groups, inventory):
    hosts = []
    for item in hosts_or_groups:
        group_hosts = inventory.get('groups', {}).get(item)
        if group_hosts:
            for host in group_hosts:
                hosts.append(inventory.get('hosts', {}).get(host, {}).get('sshHost', host))
        else:
            hosts.append(item)
    return hosts

def run_command(GroupClass, hosts, command):
    rsh.config.logging.debug(f"hosts={json.dumps(hosts)}")
    rsh.config.logging.debug(f"command='{command}'")
    try:
        group = GroupClass(*hosts)
        results = group.sudo(command, warn=True, hide=True, pty=True)

        for conn, result in results.items():
            print(f"[{conn.host}]:\n{result.stdout.strip()}")
            if len(hosts) > 1:
                print("===\n")

        return
    except Exception as e:
        rsh.config.logging.error(f"Command execution failed: {e}")
        sys.exit(1)
