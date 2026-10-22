"""Expand the shared runtime policy into either existing application root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = '      // @shared-client-runtime'


def client_root_source(source, root=ROOT):
    if source.count(MARKER) != 1:
        raise ValueError('Expected exactly one shared runtime marker in BoufbowlClient.as')
    return source.replace(MARKER, (root/'patches/ClientRuntime.as.inc').read_text().rstrip())
