"""rsh.config reads ~/.rsh.yaml at import time; point HOME at an empty directory so tests never see the developer's config."""

import os
import tempfile

os.environ['HOME'] = tempfile.mkdtemp(prefix='rsh-tests-')
