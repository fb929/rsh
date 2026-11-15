# -*- coding: utf-8 -*-
"""sr - server root: login over ssh and escalate privileges to an interactive root shell."""

import sys
import argparse
import fcntl
import getpass
import logging
import re
import signal
import struct
import termios

import gnupg
import pexpect

import rsh.config
from rsh.inventory import load_inventory, resolve_ssh_host

logger = logging.getLogger('sr')

# matches 'Password:' (su) and '[sudo] password for user:' (sudo)
PASSWORD_PROMPT_REGEX = r'[Pp]assword[^\r\n]*:'
# marker for the uid probe; the echoed command contains "$(id -u)", not digits, so it never matches itself
UID_MARKER = 'RSH_UID_'


# password file {{
def decrypt_file(gpg_file, request_passphrase=False):
    """Decrypt the gpg password file, retrying once with an interactive passphrase."""
    passphrase = None
    if request_passphrase:
        passphrase = getpass.getpass()
        if not passphrase:
            logger.error("empty passphrase")
            sys.exit(1)

    gpg = gnupg.GPG(use_agent=True)
    gpg.encoding = 'utf-8'
    try:
        with open(gpg_file, 'rb') as f:
            decrypted = gpg.decrypt_file(f, passphrase=passphrase)
    except Exception as e:
        logger.error("failed decrypt file='%s', error='%s'", gpg_file, e)
        sys.exit(1)

    if decrypted:
        return str(decrypted).rstrip()
    if request_passphrase:
        logger.error("decrypted data is empty, please check file='%s'", gpg_file)
        sys.exit(1)
    # gpg-agent could not decrypt silently, retry asking for the passphrase
    return decrypt_file(gpg_file, request_passphrase=True)


def find_root_password(password_data, host):
    """Return the password for the first '<host regex>\\t<password>' line matching host, or None."""
    for line_number, line in enumerate(password_data.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split('\t', 1)
        if len(parts) != 2:
            logger.warning("skipping line %d of password file: expected '<host regex>\\t<password>'", line_number)
            continue
        host_regex, password = parts
        if re.search(host_regex, host, re.IGNORECASE):
            return password
    return None
# }}


def get_escalate_commands(cfg):
    """Commands to try in order: 'escalatePrivilegesCommands' (list) wins,
    'escalatePrivilegesCommand' (string) is kept for backward compatibility."""
    commands = cfg['sr'].get('escalatePrivilegesCommands')
    if isinstance(commands, str):
        commands = [commands]
    if not commands:
        legacy = cfg['sr'].get('escalatePrivilegesCommand')
        if not legacy:
            logger.error("'sr.escalatePrivilegesCommands' is empty, nothing to try")
            sys.exit(1)
        commands = [legacy]
    return [str(command) for command in commands if command]


def terminal_size():
    packed = struct.pack("HHHH", 0, 0, 0, 0)
    rows, cols, _, _ = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, packed))
    return rows, cols


class SrSession:
    """One ssh session: connect, run post-login command, escalate privileges, hand over the terminal."""

    def __init__(self, host, cfg):
        self.host = host
        self.cfg = cfg
        self.timeout = cfg['sr']['pexpect']['timeout']
        self.child = None
        self._root_password = None

    # root password is decrypted lazily, only when the host actually asks for one
    @property
    def root_password(self):
        if self._root_password is None:
            password_data = decrypt_file(self.cfg['gpgFile'])
            password = find_root_password(password_data, self.host)
            if password is None:
                logger.error("no root password for host='%s' in file='%s'", self.host, self.cfg['gpgFile'])
                sys.exit(1)
            self._root_password = password
        return self._root_password

    def _expect(self, patterns):
        return self.child.expect(patterns, timeout=self.timeout)

    def _on_sigwinch(self, signum, frame):
        if self.child is not None and not self.child.closed:
            self.child.setwinsize(*terminal_size())

    def connect(self, ssh_host):
        command = '%s %s' % (self.cfg['sr']['ssh']['command'], ssh_host)
        logger.debug("spawn '%s'", command)
        self.child = pexpect.spawn(command, encoding='utf-8')
        self.child.setwinsize(*terminal_size())
        signal.signal(signal.SIGWINCH, self._on_sigwinch)
        self._expect(r'\r\n')
        print(self.child.before.rstrip())

    def run_post_login_command(self):
        command = self.cfg['sr'].get('postLoginCommand')
        if command is None:
            return
        # Wait for the command to actually finish (a provisioning script may run for
        # seconds) before escalating: append a marker echo and block until it appears.
        # Otherwise escalation starts mid-command and can mistake the command's own
        # output for a password prompt. The marker in the echoed command line carries
        # a literal '$?', so only the real output (marker + digits) matches.
        marker = 'RSH_POSTLOGIN_DONE_'
        self.child.sendline('%s; echo %s$?' % (command, marker))
        # swallow the echoed command line (with our appended marker) so it is not shown
        self._expect(r'\r\n')
        # then stream the command's real output to our stdout, so the login shows its
        # progress live, while expect() still blocks until the marker proves the command
        # has finished (otherwise escalation starts mid-command and can read the command's
        # output as a password prompt)
        self.child.logfile_read = sys.stdout
        try:
            index = self.child.expect([marker + r'(\d+)', pexpect.TIMEOUT, pexpect.EOF], timeout=self.timeout)
        finally:
            self.child.logfile_read = None
        if index != 0:
            logger.warning("postLoginCommand did not finish within %ss", self.timeout)
            return
        exit_code = int(self.child.match.group(1))
        if exit_code != 0:
            logger.warning("postLoginCommand exited with %d", exit_code)

    def _is_root_shell(self):
        """Probe the current shell with 'id -u'; True only when it answers 0."""
        self.child.sendline('echo %s$(id -u)' % UID_MARKER)
        index = self._expect([
            UID_MARKER + r'(\d+)\r\n',
            PASSWORD_PROMPT_REGEX,
            pexpect.TIMEOUT,
            pexpect.EOF,
        ])
        if index == 0:
            uid = int(self.child.match.group(1))
            logger.debug("uid=%d", uid)
            return uid == 0
        if index == 1:
            # still at a password prompt (our probe was typed into it), abort it
            logger.debug("unexpected password prompt, aborting")
            self.child.sendcontrol('c')
            self._expect(r'\r\n')
            return False
        logger.debug("no answer from host, expect index=%d", index)
        return False

    def _try_escalate(self, command):
        self.child.sendline(command)
        index = self._expect([PASSWORD_PROMPT_REGEX, r'\r\n'])
        if index == 0:
            print(self.child.before.rstrip())
            print(self.child.after.rstrip())
            self.child.sendline(self.root_password)
            self._expect(r'\r\n')
        return self._is_root_shell()

    def escalate_privileges(self):
        commands = get_escalate_commands(self.cfg)
        for command in commands:
            logger.debug("trying escalate privileges with command='%s'", command)
            if self._try_escalate(command):
                logger.debug("escalate privileges with command='%s' succeeded", command)
                return
            logger.warning("escalate privileges with command='%s' failed, trying next command", command)
        logger.error("failed escalate privileges on host='%s', all commands failed: %s", self.host, commands)
        sys.exit(1)

    def interact(self):
        self.child.interact(escape_character=None)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='login over ssh and escalate privileges')
    parser.add_argument('host', help='host for login')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--forceUseInventory', action='store_true', help='force use inventory')
    group.add_argument('-I', '--forceDontUseInventory', action='store_true', help="force don't use inventory")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    cfg = rsh.config.cfg

    if args.forceUseInventory:
        cfg['sr']['useInventorySshHost'] = True
    if args.forceDontUseInventory:
        cfg['sr']['useInventorySshHost'] = False

    if cfg['sr']['useInventorySshHost']:
        inventory = load_inventory(cfg)
        ssh_host = resolve_ssh_host(args.host, inventory, cfg['inventoryFilePath'])
    else:
        ssh_host = args.host

    session = SrSession(args.host, cfg)
    session.connect(ssh_host)
    session.run_post_login_command()
    session.escalate_privileges()
    session.interact()


if __name__ == "__main__":
    main()
