"""Resolve the hosted endpoint shared by downloadable player packages."""
import json
from pathlib import Path
from urllib.parse import urlsplit


def player_server(root, override=None):
    if override is None:
        settings = Path(root)/'resources/site.json'
        override = json.loads(settings.read_text()).get('server_url') if settings.is_file() else None
    if not isinstance(override, str) or not override:
        raise ValueError('Set server_url in resources/site.json or pass --server-url; player builds require a hosted server')
    endpoint = urlsplit(override)
    if (endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username
            or endpoint.password or endpoint.query or endpoint.fragment):
        raise ValueError('Use an HTTPS server URL without credentials, query or fragment')
    return override.rstrip('/')
