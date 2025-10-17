# exec_functions.py

import sys
import os
import yaml
import json
import argparse
import time
import logging
from braceexpand import braceexpand
from fabric import Connection
import rsh.config

logging.getLogger("paramiko").setLevel(logging.WARNING)


def parse_arguments():
    """
    Parse CLI arguments.
    Returns a tuple: (hosts_or_groups: list[str], command: str, delay: float)
    """
    prog_name = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(
        description='Execute commands via SSH on remote servers.',
        usage=(
            f"[{prog_name}] -g GROUP -c COMMAND  "
            f"or  [{prog_name}] GROUP COMMAND...  "
            f"with optional --delay SECONDS"
        ),
    )

    parser.add_argument(
        '-g', '--groups', dest='hosts_or_groups', nargs='+',
        help='Hosts or groups (supports brace expansions)'
    )
    parser.add_argument(
        '-c', '--command', nargs=argparse.REMAINDER,
        help='Command to execute'
    )
    parser.add_argument(
        'fallback', nargs=argparse.REMAINDER,
        help='Fallback: GROUP COMMAND ...'
    )
    parser.add_argument(
        '-d', '--delay', type=float, default=0.0,
        help='Delay (in seconds) between hosts when running sequentially'
    )

    args = parser.parse_args()

    if args.hosts_or_groups and args.command:
        hosts_or_groups_raw, command_parts = args.hosts_or_groups, args.command
    elif args.fallback:
        if len(args.fallback) < 2:
            parser.print_usage()
            sys.exit(1)
        hosts_or_groups_raw, command_parts = args.fallback[0], args.fallback[1:]
    else:
        parser.print_usage()
        sys.exit(1)

    hosts_or_groups = (
        list(braceexpand(hosts_or_groups_raw))
        if isinstance(hosts_or_groups_raw, str)
        else sum([list(braceexpand(x)) for x in hosts_or_groups_raw], [])
    )

    return hosts_or_groups, ' '.join(command_parts), float(args.delay)


def load_inventory():
    """Load inventory file defined in rsh.config.cfg."""
    try:
        with open(os.path.expanduser(rsh.config.cfg['inventoryFilePath']), 'r') as f:
            return yaml.load(f, Loader=yaml.Loader)
    except Exception as e:
        rsh.config.logging.error(f"Failed to load inventory: {e}")
        sys.exit(1)


def resolve_hosts(hosts_or_groups, inventory):
    """Resolve group names to actual hostnames."""
    hosts = []
    for item in hosts_or_groups:
        group_hosts = inventory.get('groups', {}).get(item)
        if group_hosts:
            for host in group_hosts:
                hosts.append(inventory.get('hosts', {}).get(host, {}).get('sshHost', host))
        else:
            hosts.append(item)
    return hosts


def run_command_sequential(hosts, command, delay=0.0):
    """
    Run a command sequentially on each host, streaming stdout/stderr immediately.
    Parameter `delay` adds a pause (in seconds) between hosts.
    """
    rsh.config.logging.debug(f"hosts={json.dumps(hosts)}")
    rsh.config.logging.debug(f"command='{command}'")
    rsh.config.logging.debug(f"delay={delay}")

    for idx, host in enumerate(hosts, 1):
        header = f"[{host}] ({idx}/{len(hosts)})"
        print(header)
        print("-" * len(header))
        try:
            conn = Connection(host)
            result = conn.sudo(command, pty=True, hide=False, warn=True)
            print(f"\n[{host}] exit status: {result.return_code}")
        except Exception as e:
            rsh.config.logging.error(f"[{host}] Command execution failed: {e}")
            print(f"[{host}] ERROR: {e}")
        finally:
            if len(hosts) > 1:
                print("===\n")

            # Optional delay between hosts
            if idx < len(hosts) and delay > 0:
                print(f"Sleeping {delay} seconds before next host...\n")
                try:
                    time.sleep(delay)
                except KeyboardInterrupt:
                    print("Sleep interrupted by user, continuing...\n")


def run_command_parallel_dedup(GroupClass, hosts, command):
    """
    Run a command in parallel across hosts and deduplicate identical outputs.
    Prints each unique output once alongside the list of hosts that produced it.
    """
    rsh.config.logging.debug(f"hosts={json.dumps(hosts)}")
    rsh.config.logging.debug(f"command='{command}'")

    try:
        group = GroupClass(*hosts)
        results = group.sudo(command, warn=True, hide=True, pty=True)

        buckets = {}     # output -> list of hosts
        exit_codes = {}  # output -> representative exit code

        for conn, res in results.items():
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()
            combined = out if out else err
            key = combined

            if key not in buckets:
                buckets[key] = []
                exit_codes[key] = res.return_code
            buckets[key].append(conn.host)

        def sort_key(item):
            _, host_list = item
            return (-len(host_list), ", ".join(sorted(host_list)))

        for output, host_list in sorted(buckets.items(), key=sort_key):
            host_line = ", ".join(sorted(host_list))
            header = f"[{host_line}]"
            print(header)
            print("-" * len(header))

            print(output if output else "(no output)")
            print(f"\nexit status (representative): {exit_codes[output]}")
            print("===\n")

    except Exception as e:
        try:
            for i in e:
                rsh.config.logging.error(f"Command execution failed: {i}")
        except Exception:
            rsh.config.logging.error(f"Command execution failed: {e}")
        sys.exit(1)
