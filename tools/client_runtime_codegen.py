"""Expand the shared runtime policy into either existing application root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = '      // @shared-client-runtime'


def client_root_source(source, root=ROOT):
    if source.count(MARKER) != 1:
        raise ValueError('Expected exactly one shared runtime marker in BoufbowlClient.as')
    # FFDec resolves fully qualified package functions as dynamic property chains
    # in replacement source. Import the timer explicitly for native AIR/Flash.
    timer_import = '   import flash.utils.getTimer;'
    if timer_import not in source:
        if '   import ' not in source:
            raise ValueError('Expected application-root import block')
        source = source.replace('   import ', timer_import+'\n   import ', 1)
    return source.replace(MARKER, (root/'patches/ClientRuntime.as.inc').read_text().rstrip())
