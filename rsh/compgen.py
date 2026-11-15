# -*- coding: utf-8 -*-
"""rshCompgen - word lists for bash completion, and the completion script itself."""

import argparse
import logging
import sys
from importlib import resources

import rsh.config
from rsh.inventory import load_inventory

logger = logging.getLogger('rshCompgen')


def completion_script():
    """Bash completion for sr/sExec/pExec; install with: eval "$(rshCompgen completion)"."""
    return resources.files('rsh').joinpath('completion.bash').read_text()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='bash completion helper for sr, sExec and pExec')
    parser.add_argument(
        'what',
        choices=['hosts', 'groups', 'completion'],
        help="'hosts' or 'groups' print inventory names, 'completion' prints the bash completion script",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.what == 'completion':
        sys.stdout.write(completion_script())
        return
    inventory = load_inventory(rsh.config.cfg)
    print(' '.join(inventory[args.what].keys()))


if __name__ == "__main__":
    main()
