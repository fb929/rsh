# exec_functions.py

import sys
import os
import yaml
import json
import argparse
from braceexpand import braceexpand
import rsh.config
import logging
from fabric import Connection  # used by sequential runner; parallel uses GroupClass

logging.getLogger("paramiko").setLevel(logging.WARNING)

def parse_arguments():
    prog_name = os.path.basename(sys.argv[0])  # detect actual script name (sExec/pExec)
    parser = argparse.ArgumentParser(
        description='Execute commands via SSH on remote servers.',
        usage=f"[{prog_name}] -g GROUP -c COMMAND  or  [{prog_name}] GROUP COMMAND..."
    )
    parser.add_argument('-g', '--groups', dest='hosts_or_groups', nargs='+',
                        help='Hosts or groups (supports brace expansions)')
    parser.add_argument('-c', '--command', nargs=argparse.REMAINDER,
                        help='Command to execute')
    parser.add_argument('fallback', nargs=argparse.REMAINDER,
                        help='Fallback: GROUP COMMAND ...')
    args = parser.parse_args()

    if args.hosts_or_groups and args.command:
        hosts_or_groups_raw, command_parts = args.hosts_or_groups, args.command
    elif args.fallback:
        hosts_or_groups_raw, command_parts = args.fallback[0], args.fallback[1:]
    else:
        parser.print_usage()
        sys.exit(1)

    hosts_or_groups = (
        list(braceexpand(hosts_or_groups_raw))
        if isinstance(hosts_or_groups_raw, str)
        else sum([list(braceexpand(x)) for x in hosts_or_groups_raw], [])
    )
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


def run_command_sequential(hosts, command):
    """
    Run a command sequentially on each host, streaming stdout/stderr immediately.
    """
    rsh.config.logging.debug(f"hosts={json.dumps(hosts)}")
    rsh.config.logging.debug(f"command='{command}'")

    for idx, host in enumerate(hosts, 1):
        header = f"[{host}] ({idx}/{len(hosts)})"
        print(header)
        print("-" * len(header))
        try:
            # hide=False => stream output directly to local stdout/stderr
            # pty=True   => allocate pseudo-terminal for unbuffered output on many tools
            # warn=True  => do not raise exceptions on non-zero exit codes
            conn = Connection(host)
            result = conn.sudo(command, pty=True, hide=False, warn=True)

            # Explicitly show the return code after the command finishes
            print(f"\n[{host}] exit status: {result.return_code}")
        except Exception as e:
            rsh.config.logging.error(f"[{host}] Command execution failed: {e}")
            print(f"[{host}] ERROR: {e}")
        finally:
            if len(hosts) > 1:
                print("===\n")


def run_command_parallel_dedup(GroupClass, hosts, command):
    """
    Run a command in parallel across hosts, then deduplicate identical outputs.
    Prints each unique output once alongside the list of hosts that produced it.

    Notes:
    - Uses hide=True to capture output for deduplication after all hosts finish.
    - Uses pty=True to encourage line-buffered behavior on remote side (safer defaults).
    - If stdout is empty and stderr has content, stderr is used for grouping.
    """
    rsh.config.logging.debug(f"hosts={json.dumps(hosts)}")
    rsh.config.logging.debug(f"command='{command}'")
    try:
        group = GroupClass(*hosts)
        results = group.sudo(command, warn=True, hide=True, pty=True)

        # Map "normalized output" -> list of hosts that produced it
        buckets = {}
        # Map "normalized output" -> representative exit code (first seen)
        exit_codes = {}

        for conn, res in results.items():
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()

            # Choose stdout if present; otherwise stderr. This keeps behavior
            # close to sequential version that primarily prints stdout.
            combined = out if out else err

            # Normalize a bit: strip trailing spaces/newlines only
            key = combined

            if key not in buckets:
                buckets[key] = []
                exit_codes[key] = res.return_code
            buckets[key].append(conn.host)

        # Stable, readable printing: group by number of hosts (desc), then alpha
        def sort_key(item):
            text, host_list = item
            return (-len(host_list), ", ".join(sorted(host_list)))

        for output, host_list in sorted(buckets.items(), key=sort_key):
            host_line = ", ".join(sorted(host_list))
            header = f"[{host_line}]"
            print(header)
            print("-" * len(header))

            if output:
                print(output)
            else:
                print("(no output)")

            print(f"\nexit status (representative): {exit_codes[output]}")
            print("===\n")

        return
    except Exception as e:
        # Fabric may raise a GroupException that is iterable; fall back to plain str(e)
        try:
            for i in e:
                rsh.config.logging.error(f"Command execution failed: {i}")
        except Exception:
            rsh.config.logging.error(f"Command execution failed: {e}")
        sys.exit(1)
