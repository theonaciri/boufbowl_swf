"""Server-authorized moderation; roles are provisioned by the local operator."""
import json
import time
from backend.storage import ServiceError


class Moderation:
    def role(self, profile):
        row=self.store.db.execute('SELECT role FROM profile_roles WHERE profile_id=?',(profile,)).fetchone()
        return row[0] if row else 'player'

    def require_moderator(self, profile):
        if self.role(profile) not in ('moderator','admin'):
            raise ServiceError('MODERATION_FORBIDDEN','Moderator role required')

    def require_can_chat(self, profile):
        row=self.store.db.execute("SELECT expires,reason FROM sanctions WHERE profile_id=? AND kind='mute' AND (expires IS NULL OR expires>?)",(profile,time.time())).fetchone()
        if row: raise ServiceError('PLAYER_MUTED',row['reason'] or 'Chat is muted')

    def moderate(self, actor, body):
        self.require_moderator(actor)
        target=self.target_player(body.get('nickname'),actor);verb=body.get('verb')
        if self.role(target)!='player' and self.role(actor)!='admin':
            raise ServiceError('MODERATOR_PROTECTED','Only an administrator can moderate another moderator')
        if verb not in ('kick','ban','mute','unban','unmute'):raise ServiceError('MODERATION_ACTION','Choose kick, ban, mute, unban or unmute')
        reason=self.name(body.get('reason') or 'Moderated by '+self.store.profile(actor)['nickname'],500)
        duration=body.get('duration',30 if verb=='kick' else 900)
        if not isinstance(duration,int) or isinstance(duration,bool) or not 0<=duration<=604800:
            raise ServiceError('MODERATION_DURATION','Duration must be seconds between 0 and 604800')
        if duration==0 and self.role(actor)!='admin':raise ServiceError('MODERATION_DURATION','Permanent sanctions require an administrator')
        expires=None if duration==0 else time.time()+duration
        if verb in ('unban','unmute'):
            self.store.db.execute('DELETE FROM sanctions WHERE profile_id=? AND kind=?',(target,verb[2:]))
        else:
            self.store.db.execute('INSERT INTO sanctions VALUES(?,?,?,?,?) ON CONFLICT(profile_id,kind) DO UPDATE SET expires=excluded.expires,reason=excluded.reason,actor=excluded.actor', (target,verb,expires,reason,actor))
            if verb in ('kick','ban'):
                self.leave_queue(target);self.cancel_challenges(target)
                if self.spectator_match(target):self.stop_spectating(target)
                match=self.store.active_match(target)
                if match:
                    side=self.side(match,target);match['score'][2-side]=max(match['score'][2-side],match['score'][side-1]+1)
                    self.end_match(match,side)
                self.store.db.execute('UPDATE presence SET seen=0 WHERE profile_id=?',(target,))
            self.store.emit(target,{'channel':'COMMUNITY','type':'MODERATED','verb':verb,'reason':reason,'expires':expires})
        self.store.db.execute('INSERT INTO moderation_audit(actor,target,action,reason,expires,created) VALUES(?,?,?,?,?,?)',(actor,target,verb,reason,expires,time.time()))
        return {'nickname':self.store.profile(target)['nickname'],'verb':verb,'expires':expires}

    def moderation_data(self, actor, offset=0):
        self.require_moderator(actor)
        rows=self.store.db.execute('SELECT a.*,p.nickname AS target_name,q.nickname AS actor_name FROM moderation_audit a JOIN profiles p ON p.id=a.target LEFT JOIN profiles q ON q.id=a.actor ORDER BY a.id DESC LIMIT 50 OFFSET ?',(offset,)).fetchall()
        reports=self.store.db.execute('SELECT r.id,p.nickname AS reporter,t.nickname AS target,r.reason,r.created FROM reports r JOIN profiles p ON p.id=r.reporter JOIN profiles t ON t.id=r.target ORDER BY r.id DESC LIMIT 50').fetchall()
        sanctions=self.store.db.execute('SELECT p.nickname,s.kind,s.expires,s.reason FROM sanctions s JOIN profiles p ON p.id=s.profile_id WHERE s.expires IS NULL OR s.expires>? ORDER BY p.nickname',(time.time(),)).fetchall()
        return {'role':self.role(actor),'audit':[dict(r) for r in rows],'reports':[dict(r) for r in reports],'sanctions':[dict(r) for r in sanctions]}

    def moderation_protocol(self, actor, payload):
        verb={1:'kick',2:'ban',3:'mute'}.get(payload.get('penalty'))
        if not verb:raise ServiceError('MODERATION_ACTION','Invalid moderation type')
        result=self.moderate(actor,{'nickname':payload['nickname'],'verb':verb,'duration':payload.get('duration',900)})
        self.emit(actor,'MODERATION_RESULT',{'resultType':1,'nickname':result['nickname'],'penalty':payload['penalty'],'penaltyEndTime':(result['expires'] or 0)*1000})
