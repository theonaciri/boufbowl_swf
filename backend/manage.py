"""Local database backup, recorded replay export/verification and report review."""
import argparse,json,sqlite3
from urllib.parse import quote
from contextlib import closing
from pathlib import Path
from backend.server import default_database
from backend.service import Service
from backend.storage import Store
from backend.replay import export_replay
from backend.tracking import backfill, metrics_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=default_database())
    sub=parser.add_subparsers(dest='operation',required=True)
    backup=sub.add_parser('backup'); backup.add_argument('output',type=Path)
    replay=sub.add_parser('replay'); replay.add_argument('match',type=int); replay.add_argument('output',type=Path); replay.add_argument('--verify',action='store_true')
    reports=sub.add_parser('reports'); reports.add_argument('--limit',type=int,default=50)
    role=sub.add_parser('role',help='Assign a role to a game nickname or account username')
    role.add_argument('nickname',metavar='NAME',help='Game nickname, or account username with --account')
    role.add_argument('role',choices=('player','moderator','admin'))
    role.add_argument('--account',action='store_true',help='Find the profile linked to this account username')
    stats=sub.add_parser('stats',help='Usage, history, online players and diagnostics (JSON)')
    stats.add_argument('--days',type=int,default=30)
    args=parser.parse_args()
    if args.operation=='stats':
        if not 1<=args.days<=365:parser.error('Choose between one and 365 days')
        if not args.database.is_file():parser.error('Database does not exist; start the server first')
        # A statistics read must never trigger the old development reset policy.
        with closing(sqlite3.connect('file:'+quote(str(args.database.resolve()))+'?mode=ro',uri=True)) as check:
            exists=check.execute("SELECT 1 FROM sqlite_master WHERE name='schema_versions'").fetchone()
            version=check.execute('SELECT MAX(version) FROM schema_versions').fetchone()[0] if exists else None
        if version!=8:parser.error('Statistics require schema 8; this database was left unchanged')
        store=Store(args.database)
        try:
            with store.transaction():backfill(store)
            with store.lock:result=metrics_report(store,args.days)
            print(json.dumps(result,indent=2))
        finally:store.close()
        return
    if args.operation=='role':
        if not args.database.is_file():
            parser.error('Database does not exist: '+str(args.database)+'; use --database to select the running server database')
        # Never create/reset a database while granting privileges.
        with closing(sqlite3.connect('file:'+quote(str(args.database.resolve()))+'?mode=rw',uri=True,timeout=10)) as db:
            db.row_factory=sqlite3.Row
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='schema_versions'").fetchone()
            version=db.execute('SELECT MAX(version) FROM schema_versions').fetchone()[0] if exists else None
            if version!=8:parser.error('Role assignment requires schema 8; this database was left unchanged')
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                name=args.nickname.strip()
                if args.account:
                    row=db.execute('SELECT p.id,p.nickname,a.username FROM accounts a JOIN profiles p ON p.id=a.profile_id WHERE a.username=?',(name,)).fetchone()
                else:
                    row=db.execute('SELECT id,nickname FROM profiles WHERE nickname=?',(name,)).fetchone()
                if not row:
                    if not args.account and db.execute('SELECT 1 FROM accounts WHERE username=?',(name,)).fetchone():
                        parser.error('That name is an account username, not a game nickname; add --account after role')
                    parser.error(('Unknown account username' if args.account else 'Unknown player nickname')+' in '+str(args.database))
                db.execute('INSERT INTO profile_roles VALUES(?,?) ON CONFLICT(profile_id) DO UPDATE SET role=excluded.role',(row['id'],args.role))
                import time
                reason='Local operator assigned '+args.role+(' via account '+row['username'] if args.account else '')
                db.execute('INSERT INTO moderation_audit(actor,target,action,reason,created) VALUES(NULL,?,?,?,?)',(row['id'],'role',reason,time.time()))
            label=row['username']+' (game nickname: '+row['nickname']+')' if args.account else row['nickname']
            print(label+': '+args.role)
        return
    if args.operation=='reports':
        store=Store(args.database)
        try:
            rows=store.db.execute('SELECT r.id,p.nickname AS reporter,t.nickname AS target,r.reason,r.created FROM reports r JOIN profiles p ON p.id=r.reporter JOIN profiles t ON t.id=r.target ORDER BY r.id DESC LIMIT ?', (max(1,min(500,args.limit)),)).fetchall()
            print(json.dumps([dict(r) for r in rows],indent=2))
        finally: store.close()
        return
    if args.operation=='backup':
        store=Store(args.database)
        try: store.backup(args.output)
        finally: store.close()
    else:
        service=Service(args.database)
        try:
            with service.store.transaction(): result=export_replay(service,args.match,args.verify)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
        finally: service.close()
    print(args.output)


if __name__=='__main__': main()
