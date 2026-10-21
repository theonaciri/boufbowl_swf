"""Resolve Android signing credentials before starting expensive package builds."""
import ast
import getpass
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tools.build_tools import BuildError, CACHE

ROOT = Path(__file__).resolve().parent.parent


def _save_password(path, password):
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.read_text().strip() != password:
            raise BuildError(f'Signing password file changed during setup: {path}') from None
        return
    with os.fdopen(descriptor, 'w') as output:
        output.write(password+'\n')


def _matches(certificate, password, jdk):
    keytool = Path(jdk)/('bin/keytool.exe' if os.name == 'nt' else 'bin/keytool')
    if not keytool.is_file():
        raise BuildError(f'JDK signing tool is missing: {keytool}')
    # Use an environment reference so the password is absent from command arguments/logs.
    try:
        result = subprocess.run([str(keytool), '-list', '-storetype', 'PKCS12',
                                 '-keystore', str(certificate), '-storepass:env', 'BOUFBOWL_SIGNING_CHECK'],
                                env={**os.environ, 'BOUFBOWL_SIGNING_CHECK': password},
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        raise BuildError(f'Could not validate Android signing certificate: {certificate}') from None
    return result.returncode == 0


def _legacy_password(certificate, jdk):
    """Migrate only the known historical development default, after verification."""
    try:
        # Do not reintroduce a fixed password in current code or require full Git history.
        source = subprocess.run(['git', 'show', 'd711230^:android/build.py'], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        if source.returncode:
            return None
        tree = ast.parse(source.stdout)
    except (OSError, subprocess.TimeoutExpired, SyntaxError):
        return None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'password' for target in node.targets)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            password = node.value.value
            if _matches(certificate, password, jdk):
                return password
    return None


def signing_credentials(jdk, keystore=None):
    local = keystore is None
    certificate = Path(keystore).expanduser().resolve() if keystore else CACHE/'android-signing/local.p12'
    password_file = certificate.with_suffix('.password')
    if not local and not certificate.is_file():
        raise BuildError(f'Android signing certificate not found: {certificate}')
    certificate.parent.mkdir(parents=True, exist_ok=True)
    password = os.environ.get('BOUFBOWL_KEYSTORE_PASSWORD')
    if not password and password_file.is_file():
        password = password_file.read_text().strip()
        if not password:
            raise BuildError(f'The signing password file is empty: {password_file}')
        password_file.chmod(0o600)
    if password:
        if certificate.exists() and not _matches(certificate, password, jdk):
            raise BuildError(f'Cannot open signing certificate {certificate} with the supplied/saved password. '
                             f'Check BOUFBOWL_KEYSTORE_PASSWORD or {password_file}. The certificate was preserved.')
        if local and not password_file.exists():
            _save_password(password_file, password)
        return certificate, password
    if not certificate.exists():
        password = secrets.token_urlsafe(32)
        _save_password(password_file, password)
        return certificate, password
    if local:
        password = _legacy_password(certificate, jdk)
        if password:
            _save_password(password_file, password)
            print('Migrated legacy Android signing password; existing certificate preserved.', flush=True)
            return certificate, password
    if sys.stdin.isatty():
        print(f'Android signing certificate: {certificate}', flush=True)
        try:
            password = getpass.getpass('Existing certificate password (hidden): ')
        except EOFError:
            password = ''
        if password and _matches(certificate, password, jdk):
            if local:
                _save_password(password_file, password)
            return certificate, password
        raise BuildError('The certificate password was not accepted. The existing certificate was preserved.')
    raise BuildError(f'Existing signing certificate {certificate} has no available password. '
                     f'Run the command in an interactive terminal to enter it privately, restore {password_file}, '
                     'or supply BOUFBOWL_KEYSTORE_PASSWORD. The existing certificate was preserved.')
