"""Optional username/password accounts linked to persisted device profiles."""
import hashlib
import hmac
import re
import secrets
import time
from backend.storage import ServiceError

ITERATIONS = 600_000


def credentials(body, field='password'):
    username=body.get('username','')
    password=body.get(field)
    if not isinstance(username,str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{3,32}',username):
        raise ServiceError('ACCOUNT_USERNAME','Username must contain 3–32 letters, digits, dots, dashes or underscores')
    if not isinstance(password,str) or not 10<=len(password)<=128:
        raise ServiceError('ACCOUNT_PASSWORD','Password must contain 10–128 characters')
    return username.lower(),password


def password_hash(password,salt,iterations=ITERATIONS):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),iterations).hex()


class Accounts:
    def account(self, body, peer='local'):
        action=body.get('action')
        if action in ('export', 'delete'):
            from backend.account_privacy import privacy_action
            return privacy_action(self, body, peer)
        if action=='logout':
            with self.store.transaction():
                profile=self.store.authenticate(body.get('session'))
                self.leave_queue(profile)
                self.store.db.execute('DELETE FROM sessions WHERE token_hash=?',(self.store.digest(body['session']),))
            return {'ok':True}
        if action not in ('register','login','password','recover'):
            raise ServiceError('ACCOUNT_ACTION','Choose register, login, password, recover or logout')
        username,password=credentials(body,'new_password' if action=='recover' else 'password')
        error=None; recovery_code=None
        with self.store.transaction():
            # Persist failures even when authentication fails. Peer is supplied
            # by the HTTP handler, never by an untrusted JSON field.
            bucket=self.store.digest(str(peer)+'|'+username)
            attempt=self.store.db.execute('SELECT * FROM auth_attempts WHERE bucket=?',(bucket,)).fetchone()
            if attempt and attempt['reset_at']>time.time() and attempt['failures']>=5:
                raise ServiceError('ACCOUNT_RATE_LIMIT','Too many attempts; try again in five minutes')
            row=self.store.db.execute('SELECT * FROM accounts WHERE username=?',(username,)).fetchone()
            if action=='register' and not row:
                profile=self.store.authenticate(body['session']) if body.get('session') else self.create_device({**body,'nickname':body.get('nickname') or username[:30]})[0]
                if self.store.db.execute('SELECT 1 FROM accounts WHERE profile_id=?',(profile,)).fetchone():
                    raise ServiceError('ACCOUNT_LINKED','This profile is already linked to an account')
                salt=secrets.token_hex(16)
                self.store.db.execute('INSERT INTO accounts(username,profile_id,salt,password_hash,iterations,created) VALUES(?,?,?,?,?,?)',
                    (username,profile,salt,password_hash(password,salt),ITERATIONS,time.time()))
                recovery_code=secrets.token_urlsafe(32)
                self.store.db.execute('UPDATE accounts SET recovery_hash=? WHERE profile_id=?',(self.store.digest(recovery_code),profile))
                token=self.store.issue_session(profile,'account')
            else:
                if action=='recover':
                    code=body.get('recovery_code')
                    valid=isinstance(code,str) and 32<=len(code)<=128 and hmac.compare_digest(
                        self.store.digest(code),row['recovery_hash'] or '' if row else '')
                else:
                    valid=hmac.compare_digest(password_hash(password,row['salt'] if row else '0'*32,
                                              row['iterations'] if row else ITERATIONS),row['password_hash'] if row else '0'*64)
                if not row or not valid:
                    failures=attempt['failures']+1 if attempt and attempt['reset_at']>time.time() else 1
                    reset=attempt['reset_at'] if attempt and attempt['reset_at']>time.time() else time.time()+300
                    self.store.db.execute('INSERT OR REPLACE INTO auth_attempts VALUES(?,?,?)',(bucket,failures,reset))
                    error=ServiceError('ACCOUNT_AUTH','Invalid username or credentials')
                else:
                    profile=row['profile_id']
                    if action=='register':
                        # Lost-response retry may reclaim only its own device profile.
                        if not body.get('session') or self.store.authenticate(body['session'])!=profile:
                            error=ServiceError('ACCOUNT_EXISTS','Username is already registered; use login')
                    elif action in ('password','recover'):
                        if action=='password' and self.store.authenticate(body.get('session'))!=profile:
                            raise ServiceError('ACCOUNT_OWNERSHIP','Sign in to this account first')
                        _,new=credentials(body,'new_password');salt=secrets.token_hex(16)
                        self.store.db.execute('UPDATE accounts SET salt=?,password_hash=?,iterations=? WHERE username=?',
                                              (salt,password_hash(new,salt),ITERATIONS,username))
                        self.store.db.execute('DELETE FROM sessions WHERE profile_id=?',(profile,))
                        self.leave_queue(profile)
                        recovery_code=secrets.token_urlsafe(32)
                        self.store.db.execute('UPDATE accounts SET recovery_hash=? WHERE profile_id=?',(self.store.digest(recovery_code),profile))
                    if error is None: token=self.store.issue_session(profile,'account')
            if error is None:
                if body.get('session'):
                    try: self.leave_queue(self.store.authenticate(body['session']))
                    except ServiceError: pass
                self.store.db.execute('DELETE FROM auth_attempts WHERE bucket=?',(bucket,))
        if error: raise error
        result=self.hello({'session':token,'client_id':body.get('client_id'),'client':body.get('client')})
        if recovery_code: result['recovery_code']=recovery_code
        return result
