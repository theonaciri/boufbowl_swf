"""Local database backup, recorded replay export/verification and report review."""
import argparse,json
from pathlib import Path
from backend.server import default_database
from backend.service import Service
from backend.storage import Store
from backend.replay import export_replay


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=default_database())
    sub=parser.add_subparsers(dest='operation',required=True)
    backup=sub.add_parser('backup'); backup.add_argument('output',type=Path)
    replay=sub.add_parser('replay'); replay.add_argument('match',type=int); replay.add_argument('output',type=Path); replay.add_argument('--verify',action='store_true')
    reports=sub.add_parser('reports'); reports.add_argument('--limit',type=int,default=50)
    role=sub.add_parser('role');role.add_argument('nickname');role.add_argument('role',choices=('player','moderator','admin'))
    args=parser.parse_args()
    if args.operation=='role':
        store=Store(args.database)
        try:
            with store.transaction():
                row=store.db.execute('SELECT id FROM profiles WHERE nickname=?',(args.nickname,)).fetchone()
                if not row:parser.error('Unknown player nickname')
                store.db.execute('INSERT INTO profile_roles VALUES(?,?) ON CONFLICT(profile_id) DO UPDATE SET role=excluded.role',(row[0],args.role))
                import time
                store.db.execute('INSERT INTO moderation_audit(actor,target,action,reason,created) VALUES(NULL,?,?,?,?)',(row[0],'role','Local operator assigned '+args.role,time.time()))
            print(args.nickname+': '+args.role)
        finally:store.close()
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
