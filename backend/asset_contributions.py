"""Quarantined restoration contributions. Raw uploads are never publicly served."""
from collections import Counter
import hashlib
from datetime import datetime
import hmac
import ipaddress
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shutil
import sqlite3
import struct
import subprocess
import threading
import time
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zlib
from backend.storage import ServiceError
from tools.build_restoration_data import audit

FORMATS={'.mp3':('audio/mpeg',20*1024*1024),'.png':('image/png',8*1024*1024),
         '.webp':('image/webp',8*1024*1024),'.swl':('application/octet-stream',8*1024*1024),
         '.swf':('application/x-shockwave-flash',8*1024*1024),'.dae':('model/vnd.collada+xml',8*1024*1024)}
MAX_STORAGE=512*1024*1024


def fail(message,code='ASSET_INVALID'):
    raise ServiceError(code,message)


def catalog(root):
    result={}
    inventory=Path(root)/'assets/site/restoration/inventory.json'
    data=json.loads(inventory.read_text()) if inventory.is_file() else audit(root)
    for item in data['asset_status']:
        path=item['path']
        if not path or item['status']=='found' or Path(path).suffix not in FORMATS:continue
        relative=Path(path)
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0]!='assets':continue
        identity=hashlib.sha256(path.encode()).hexdigest()[:24]
        mime,limit=FORMATS[relative.suffix]
        result[identity]={**item,'id':identity,'name':relative.name,'extension':relative.suffix,'mime':mime,'max_bytes':limit}
    return result


def sandbox(command,input_path,output_dir,definitions=None,timeout=30,memory=1024*1024*1024,extra=(),file_limit=33554432):
    """Read-only system files, one input, one output directory; no network or app data."""
    if not shutil.which('bwrap') or not shutil.which('prlimit'):fail('Isolation indisponible.','ASSET_SCANNER')
    args=['prlimit','--cpu=30',f'--as={memory}','--fsize='+str(96*1024*1024 if definitions else file_limit),'--nofile=128','--',
          'bwrap','--unshare-all','--die-with-parent','--new-session','--ro-bind','/usr','/usr']
    for folder in ('/lib','/lib64'):
        if Path(folder).exists():args+=['--ro-bind',folder,folder]
    if Path('/etc/ld.so.cache').exists():args+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
    args+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/work',
           '--ro-bind',str(input_path.resolve()),'/work/input'+input_path.suffix,
           '--bind',str(output_dir.resolve()),'/output','--chdir','/work','--setenv','HOME','/tmp']
    for source,target in extra:args+=['--ro-bind',str(source),target]
    if definitions:
        args+=['--ro-bind',str(definitions),'/definitions']
        if Path('/etc/clamav/certs').is_dir():args+=['--ro-bind','/etc/clamav/certs','/etc/clamav/certs']
    return subprocess.run(args+['--']+command,capture_output=True,timeout=timeout,check=False)


class AssetContributions:
    def __init__(self,root,directory,scanner=None,start=True):
        self.root=Path(root).resolve();self.directory=Path(directory).resolve()
        if self.directory==self.root or any(self.directory.is_relative_to(self.root/p) for p in ('assets','resources','vendor','bin')):raise ValueError('Quarantine cannot be public')
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(self.directory,0o700)
        self.lock=threading.RLock();self.db=sqlite3.connect(self.directory/'reviews.sqlite',check_same_thread=False,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE IF NOT EXISTS tokens(hash TEXT PRIMARY KEY,ip TEXT,asset TEXT,created REAL,used INTEGER DEFAULT 0);
          CREATE TABLE IF NOT EXISTS submissions(id TEXT PRIMARY KEY,asset TEXT,path TEXT,name TEXT,ip TEXT,created REAL,
            state TEXT,size INTEGER,sha256 TEXT,scan_signature TEXT,scanned REAL,error TEXT,metadata TEXT,actor TEXT,reviewed REAL);
          CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY,submission TEXT,actor TEXT,action TEXT,created REAL);
        ''')
        salt=self.db.execute("SELECT value FROM settings WHERE key='salt'").fetchone()
        self.salt=salt[0] if salt else secrets.token_hex(32)
        self.db.execute("INSERT OR IGNORE INTO settings VALUES('salt',?)",(self.salt,))
        self.scanner=scanner;self.jobs=queue.Queue(maxsize=8);self.stopping=threading.Event()
        self.worker=threading.Thread(target=self.run,daemon=True)
        self.db.execute("UPDATE submissions SET state='scan_error',error='Analyse interrompue : relancer le contrôle.' WHERE state IN ('receiving','queued','scanning')")
        if start:self.worker.start()

    def close(self):
        self.stopping.set()
        if self.worker.is_alive():self.worker.join(timeout=300)
        self.db.close()

    def ip_hash(self,ip):return hmac.new(self.salt.encode(),str(ip).encode(),hashlib.sha256).hexdigest()

    def signature(self):
        folder=Path('/var/lib/clamav');files=[p for p in folder.glob('*') if p.suffix in ('.cvd','.cld')]
        daily=[p for p in files if p.name.startswith('daily.')]
        if not shutil.which('clamscan') or not daily or time.time()-max(p.stat().st_mtime for p in daily)>72*3600:
            fail('Antivirus indisponible ou signatures trop anciennes.','ASSET_SCANNER')
        try:
            with daily[0].open('rb') as header:stamp=header.read(512).decode('ascii','ignore').split(':')[1]
            if time.time()-datetime.strptime(stamp,'%d %b %Y %H-%M %z').timestamp()>72*3600:fail('Signatures trop anciennes.','ASSET_SCANNER')
        except (ValueError,IndexError):fail('Date des signatures inconnue.','ASSET_SCANNER')
        return hashlib.sha256('|'.join(f'{p.name}:{p.stat().st_size}:{p.stat().st_mtime_ns}' for p in sorted(files)).encode()).hexdigest()

    def scan(self,path,output):
        if self.scanner:return self.scanner(path,output)
        signature=self.signature()
        result=sandbox(['clamscan','--database=/definitions','--no-summary','--infected','--scan-swf=yes',
            '--alert-encrypted=yes','--alert-exceeds-max=yes','--max-filesize=32M','--max-scansize=64M',
            '--max-recursion=4','--max-files=20','/work/input'+path.suffix],path,output,
            definitions=Path('/var/lib/clamav'),timeout=90,memory=4*1024**3)
        if result.returncode==1:fail('Fichier bloqué par l’antivirus.','ASSET_INFECTED')
        if result.returncode!=0:fail('Analyse antivirus impossible.','ASSET_SCANNER')
        return signature

    def cleanup(self):
        now=time.time()
        self.db.execute('DELETE FROM tokens WHERE created<?',(now-3600,))
        for row in self.db.execute("SELECT id FROM submissions WHERE created<? AND state NOT IN ('approved','published')",(now-14*86400,)).fetchall():
            shutil.rmtree(self.directory/row['id'],ignore_errors=True)
            self.db.execute('DELETE FROM decisions WHERE submission=?',(row['id'],));self.db.execute('DELETE FROM submissions WHERE id=?',(row['id'],))
        self.db.execute("UPDATE submissions SET ip='' WHERE created<?",(now-30*86400,))

    def token(self,asset,ip,consent):
        if consent is not True:fail('Confirmez votre autorisation de transmettre ce fichier.')
        with self.lock:
            self.cleanup();items=catalog(self.root)
            if not isinstance(asset,str) or asset not in items:fail('Cette ressource ne reçoit pas de contribution.')
            address=self.ip_hash(ip);now=time.time()
            if self.db.execute('SELECT COUNT(*) FROM tokens').fetchone()[0]>=500:fail('Trop de demandes sur le serveur.','ASSET_LIMIT')
            if self.db.execute('SELECT COUNT(*) FROM tokens WHERE ip=? AND created>?',(address,now-3600)).fetchone()[0]>=30:
                fail('Trop de demandes. Réessayez dans une heure.','ASSET_LIMIT')
            token=secrets.token_urlsafe(32)
            self.db.execute('INSERT INTO tokens(hash,ip,asset,created) VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),address,asset,now))
            return {'ok':True,'token':token,'asset':items[asset],'expires_in':600}

    def reserve(self,asset,token,name,size,ip):
        with self.lock:
            now=time.time();address=self.ip_hash(ip);item=catalog(self.root).get(asset)
            if not item or unquote(name)!=item['name']:fail('Nom exact et ressource attendus obligatoires.')
            if not isinstance(size,int) or not 0<size<=item['max_bytes']:fail('Taille du fichier hors limite.','ASSET_LIMIT')
            nonce=self.db.execute('SELECT * FROM tokens WHERE hash=?',(hashlib.sha256(str(token).encode()).hexdigest(),)).fetchone()
            if not nonce or nonce['used'] or nonce['created']<now-600 or nonce['asset']!=asset or nonce['ip']!=address:fail('Autorisation expirée. Rouvrez le formulaire.','ASSET_TOKEN')
            rows=self.db.execute('SELECT created,state FROM submissions WHERE ip=? AND created>?',(address,now-86400)).fetchall()
            active=self.db.execute("SELECT COUNT(*) FROM submissions WHERE state IN ('receiving','queued','scanning')").fetchone()[0]
            if len(rows)>=30 or sum(r['created']>now-3600 for r in rows)>=10 or active>=8 or self.jobs.full():
                fail('Limite atteinte : 10 envois/heure, 30/jour ou file d’attente pleine.','ASSET_LIMIT')
            if self.db.execute('SELECT COUNT(*) FROM submissions WHERE created>?',(now-86400,)).fetchone()[0]>=100:fail('Quota quotidien du serveur atteint.','ASSET_LIMIT')
            if self.db.execute("SELECT COUNT(*) FROM submissions WHERE asset=? AND state NOT IN ('rejected','published','expired')",(asset,)).fetchone()[0]>=3:fail('Trois propositions sont déjà en cours pour cette ressource.','ASSET_LIMIT')
            occupied=sum(p.stat().st_size for p in self.directory.rglob('*') if p.is_file())
            reserved=self.db.execute("SELECT COALESCE(SUM(size),0) FROM submissions WHERE state='receiving'").fetchone()[0]
            if occupied+reserved+size+64*1024*1024>MAX_STORAGE:fail('Espace de quarantaine saturé.','ASSET_LIMIT')
            identity=secrets.token_hex(16);folder=self.directory/identity;folder.mkdir(mode=0o700)
            self.db.execute('UPDATE tokens SET used=1 WHERE hash=?',(nonce['hash'],))
            self.db.execute('INSERT INTO submissions(id,asset,path,name,ip,created,state,size) VALUES(?,?,?,?,?,?,?,?)',
                (identity,asset,item['path'],item['name'],address,now,'receiving',size))
            return identity,folder/('source'+item['extension'])

    def finish(self,identity,path):
        with self.lock:
            os.chmod(path,0o600)
            self.db.execute("UPDATE submissions SET state='queued',sha256=? WHERE id=?",(hashlib.sha256(path.read_bytes()).hexdigest(),identity))
            self.jobs.put_nowait(identity)

    def abort(self,identity):
        with self.lock:
            self.db.execute("UPDATE submissions SET state='rejected',error='Envoi incomplet.' WHERE id=?",(identity,))
            shutil.rmtree(self.directory/identity,ignore_errors=True)

    def validate(self,path,output,target):
        extension=path.suffix;data=path.read_bytes()
        if extension in ('.swl','.swf'):
            symbols=[]
            if extension=='.swl':
                if len(data)<12 or data[:2]!=b'L\0':fail('En-tête SWL Ankama attendu.')
                rate=int.from_bytes(data[2:6],'big');count=int.from_bytes(data[6:10],'big');offset=10
                if not 1<=rate<=120 or not 1<=count<=10000:fail('Table de symboles SWL invalide.')
                for _ in range(count):
                    size=int.from_bytes(data[offset:offset+2],'big');offset+=2
                    if not 0<size<=512 or offset+size>len(data):fail('Symbole SWL invalide.')
                    name=data[offset:offset+size].decode('utf8');offset+=size
                    if len(symbols)<40:symbols.append(name)
                data=data[offset:]
            if len(data)<12 or data[:3] not in (b'FWS',b'CWS'):fail('Signature Flash FWS/CWS attendue.')
            declared=int.from_bytes(data[4:8],'little')
            if not 12<=declared<=32*1024*1024:fail('Taille Flash décompressée excessive.')
            if data[:3]==b'CWS':
                decoder=zlib.decompressobj();body=decoder.decompress(data[8:],declared-7)
                if not decoder.eof or decoder.unused_data or len(body)!=declared-8:fail('Compression Flash invalide ou excessive.')
            else:
                body=data[8:]
                if len(data)!=declared:fail('Longueur Flash incorrecte.')
            # Bodies should not access the network, filesystem or browser scripting bridge.
            for unsafe in (b'ExternalInterface',b'URLRequest',b'Socket',b'navigateToURL',b'FileReference',b'flash.filesystem'):
                if unsafe in body:fail('Capacité active interdite dans cette ressource Flash.')
            offset=(5+4*(body[0]>>3)+7)//8;frames=int.from_bytes(body[offset+2:offset+4],'little');offset+=4
            tags=Counter();labels=[];sprites=[]
            while offset+2<=len(body):
                value=int.from_bytes(body[offset:offset+2],'little');offset+=2;kind=value>>6;size=value&63
                if size==63:
                    if offset+4>len(body):fail('Tag Flash tronqué.')
                    size=int.from_bytes(body[offset:offset+4],'little');offset+=4
                if offset+size>len(body):fail('Tag Flash hors limites.')
                if kind in (57,71):fail('Import externe Flash interdit.')
                if kind==39 and size>=4 and len(sprites)<4:sprites.append(int.from_bytes(body[offset:offset+2],'little'))
                if kind==43 and len(labels)<40:labels.append(body[offset:offset+min(size,120)].split(b'\0')[0].decode('utf8','replace'))
                tags[kind]+=1;offset+=size
                if sum(tags.values())>100000:fail('Trop de tags Flash.')
                if kind==0:break
            if not frames or not tags:fail('Animation Flash vide.')
            expanded=output/'expanded.swf';expanded.write_bytes(b'FWS'+data[3:8]+body)
            self.scan(expanded,output)
            thumbnails=self.flash_thumbnails(expanded,output,sprites)
            expanded.unlink()
            return {'kind':'flash','version':data[3],'frames':frames,'tags':dict(tags),'labels':labels,'symbols':symbols,'thumbnails':thumbnails,
                    'notice':'Aperçu statique des éléments disponibles et propriétés du fichier ; aucun ActionScript n’est exécuté.'}
        if extension=='.dae':
            if b'\x00' in data:fail('XML UTF-8 attendu.')
            if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():fail('DTD et entités XML interdites.')
            if data.count(b'<')>100000:fail('Modèle trop complexe.')
            tree=ET.fromstring(data)
            if tree.tag.split('}')[-1]!='COLLADA':fail('Document COLLADA attendu.')
            count=0;vertices=[]
            for element in tree.iter():
                count+=1
                if count>100000:fail('Modèle trop complexe.')
                tag=element.tag.split('}')[-1]
                if tag=='init_from' and element.text:
                    ref=element.text.strip()
                    if ':' in ref or ref.startswith(('/', '\\')) or not (self.root/target).parent.joinpath(ref).resolve().is_relative_to(self.root/'assets'):
                        fail('Référence externe au modèle interdite.')
                if tag=='float_array' and len(vertices)<9000 and 'position' in element.get('id','').lower():
                    values=(element.text or '').split()
                    if len(values)>300000:fail('Trop de coordonnées.')
                    for value in values[:9000-len(vertices)]:
                        number=float(value)
                        if not -1e9<number<1e9:fail('Coordonnée invalide.')
                        vertices.append(number)
            return {'kind':'model','elements':count,'vertices':vertices,'notice':'Nuage de points des positions ; aucune texture distante n’est chargée.'}
        if not shutil.which('ffprobe') or not shutil.which('ffmpeg'):fail('Prévisualisation indisponible.','ASSET_SCANNER')
        probe=sandbox(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_streams','-show_format','-of','json','/work/input'+extension],path,output)
        if probe.returncode:fail('Fichier multimédia illisible.')
        metadata=json.loads(probe.stdout);streams=metadata.get('streams',[])
        if extension=='.mp3':
            if len(streams)!=1 or streams[0].get('codec_name')!='mp3' or streams[0].get('codec_type')!='audio':fail('Un fichier MP3 audio sans image jointe est attendu.')
            duration=float(metadata['format'].get('duration',0));channels=streams[0].get('channels',0)
            if not 0<duration<=900 or channels not in (1,2):fail('Audio limité à 15 minutes et deux canaux.')
            args=['-vn','-t','30','-ar','22050','-ac','1','-c:a','pcm_s16le','/output/preview.wav'];kind='audio'
        else:
            expected={'.png':'png','.webp':'webp'}[extension]
            if len(streams)!=1 or streams[0].get('codec_name')!=expected:fail('Format réel différent du format attendu.')
            width=streams[0].get('width',0);height=streams[0].get('height',0)
            if not 0<width<=8192 or not 0<height<=8192 or width*height>40000000 or b'ANIM' in data[:256] or b'acTL' in data[:256]:fail('Image trop grande ou animée.')
            args=['-frames:v','1','-vf','scale=512:512:force_original_aspect_ratio=decrease','/output/preview.png'];kind='image'
        converted=sandbox(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file,pipe','-i','/work/input'+extension,'-map_metadata','-1',*args],path,output)
        if converted.returncode:fail('Prévisualisation isolée impossible.')
        return {'kind':kind,'duration':duration if kind=='audio' else None,'codec':streams[0]['codec_name']}

    def flash_thumbnails(self,path,output,sprites):
        if not sprites:return 0
        cache=Path.home()/'.cache/boufbowl-flash-tools'
        jar=Path(os.environ.get('FFDEC_JAR',cache/'ffdec-26.3.0/ffdec.jar'))
        homes=list((cache/'jdk-17').glob('jdk-*'))
        home=Path(os.environ.get('BOUFBOWL_ASSET_JAVA_HOME',str(homes[0]) if homes else '/nonexistent'))
        if not jar.is_file() or not (home/'bin/java').is_file():return 0
        try:
            result=sandbox(['/java/bin/java','-Xmx384m','-XX:CompressedClassSpaceSize=64m','-XX:ReservedCodeCacheSize=64m',
                '-Djava.awt.headless=true','-jar','/tool/ffdec.jar','-select',','.join(f'{sprite}:1' for sprite in sprites),'-selectid',','.join(map(str,sprites)),
                '-exportTimeout','15','-export','sprite','/output/flash','/work/input.swf'],path,output,
                extra=[(jar.parent.resolve(),'/tool'),(home.resolve(),'/java'),(Path('/etc/fonts'),'/etc/fonts')],timeout=25,memory=2*1024**3,file_limit=4*1024**2)
            if result.returncode:return 0
            count=0
            for candidate in sorted((output/'flash').rglob('*.png'))[:4]:
                probe=sandbox(['ffprobe','-v','error','-show_streams','-of','json','/work/input.png'],candidate,output)
                if probe.returncode:continue
                stream=json.loads(probe.stdout)['streams'][0]
                if stream.get('codec_name')!='png' or not 0<stream.get('width',0)*stream.get('height',0)<=40000000:continue
                converted=sandbox(['ffmpeg','-v','error','-nostdin','-y','-i','/work/input.png','-map_metadata','-1',
                    '-frames:v','1','-vf','scale=512:512:force_original_aspect_ratio=decrease',f'/output/flash-{count}.png'],candidate,output)
                if converted.returncode==0:count+=1
            return count
        except (OSError,subprocess.SubprocessError,ValueError,KeyError,IndexError):return 0
        finally:shutil.rmtree(output/'flash',ignore_errors=True)

    def process(self,identity):
        with self.lock:
            row=self.db.execute('SELECT * FROM submissions WHERE id=?',(identity,)).fetchone()
            if not row or row['state']!='queued':return
            self.db.execute("UPDATE submissions SET state='scanning' WHERE id=?",(identity,))
        folder=self.directory/identity;path=folder/('source'+Path(row['name']).suffix)
        try:
            for old in folder.iterdir():
                if old!=path:
                    if old.is_dir():shutil.rmtree(old)
                    else:old.unlink()
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:fail('Empreinte du fichier altérée.')
            signature=self.scan(path,folder)
            metadata=self.validate(path,folder,row['path'])
            with self.lock:self.db.execute("UPDATE submissions SET state='pending',scan_signature=?,scanned=?,metadata=?,error=NULL WHERE id=?",(signature,time.time(),json.dumps(metadata),identity))
        except Exception as error:
            state='blocked' if (isinstance(error,ServiceError) and error.code!='ASSET_SCANNER') or (not isinstance(error,ServiceError) and isinstance(error,(ValueError,ET.ParseError,zlib.error,struct.error,IndexError))) else 'scan_error'
            with self.lock:self.db.execute('UPDATE submissions SET state=?,error=? WHERE id=?',(state,str(error)[:300],identity))
            if state=='blocked':
                for file in folder.iterdir():file.unlink(missing_ok=True)

    def run(self):
        last_cleanup=0
        while not self.stopping.is_set():
            try:identity=self.jobs.get(timeout=1)
            except queue.Empty:
                if time.monotonic()-last_cleanup>60:
                    with self.lock:self.cleanup()
                    last_cleanup=time.monotonic()
                continue
            self.process(identity);self.jobs.task_done()

    def listing(self,state=''):
        with self.lock:
            self.cleanup()
            if state not in ('','pending','queued','scanning','blocked','scan_error','approved','rejected','published'):fail('Filtre inconnu.')
            rows=self.db.execute('SELECT * FROM submissions '+('WHERE state=? ' if state else '')+'ORDER BY created DESC LIMIT 100',([state] if state else [])).fetchall()
            result=[]
            for row in rows:
                item=dict(row);item.pop('ip');item['metadata']=json.loads(item['metadata']) if item['metadata'] else None;result.append(item)
            return {'submissions':result,'counts':dict(self.db.execute('SELECT state,COUNT(*) FROM submissions GROUP BY state').fetchall()),'limits':{'storage_bytes':MAX_STORAGE,'queue':8,'per_hour':10,'per_day':30}}

    def decision(self,identity,action,actor):
        if not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{32}',identity):fail('Contribution inconnue.')
        with self.lock:
            row=self.db.execute('SELECT * FROM submissions WHERE id=?',(identity,)).fetchone()
            if not row:fail('Contribution inconnue.')
            folder=self.directory/identity;path=folder/('source'+Path(row['name']).suffix)
            if action=='archive':
                if row['state']!='approved':fail('Approuvez d’abord ce fichier.')
                shutil.rmtree(folder,ignore_errors=True);state='published'
            elif action=='reject':
                if row['state'] in ('receiving','scanning'):fail('Attendez la fin du traitement en cours.')
                if row['state']=='published':fail('Une ressource déployée ne se rejette pas rétroactivement.')
                shutil.rmtree(folder,ignore_errors=True);state='rejected'
            elif action=='rescan':
                if row['state'] not in ('pending','scan_error','approved') or not path.is_file():fail('Réanalyse impossible.')
                if self.jobs.full():fail('File d’attente pleine.','ASSET_LIMIT')
                self.db.execute("UPDATE submissions SET state='queued',metadata=NULL WHERE id=?",(identity,));self.jobs.put_nowait(identity);state='queued'
            elif action=='approve':
                if row['state']!='pending' or not row['scanned'] or time.time()-row['scanned']>3600:fail('Une analyse récente et réussie est requise.')
                signature=self.signature() if not self.scanner else row['scan_signature']
                if signature!=row['scan_signature'] or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:fail('Fichier ou signatures modifiés : relancez l’analyse.')
                state='approved'
            else:fail('Décision inconnue.')
            self.db.execute('UPDATE submissions SET state=?,actor=?,reviewed=? WHERE id=?',(state,actor,time.time(),identity))
            self.db.execute('INSERT INTO decisions(submission,actor,action,created) VALUES(?,?,?,?)',(identity,actor,action,time.time()))
            return {'ok':True,'state':state}

    def preview(self,identity,index=0):
        if not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{32}',identity):fail('Contribution inconnue.')
        with self.lock:
            row=self.db.execute('SELECT state,metadata FROM submissions WHERE id=?',(identity,)).fetchone()
            if not row or row['state'] not in ('pending','approved'):fail('Prévisualisation indisponible.')
            metadata=json.loads(row['metadata'])
            if metadata['kind']=='flash' and metadata.get('thumbnails'):
                if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<metadata['thumbnails']:fail('Aperçu inconnu.')
                return (self.directory/identity/f'flash-{index}.png').read_bytes(),'image/png'
            if metadata['kind'] not in ('image','audio'):fail('Ce format dispose uniquement d’un aperçu technique.')
            name,mime=('preview.png','image/png') if metadata['kind']=='image' else ('preview.wav','audio/wav')
            return (self.directory/identity/name).read_bytes(),mime

    def original(self,identity):
        if not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{32}',identity):fail('Contribution inconnue.')
        with self.lock:
            row=self.db.execute('SELECT * FROM submissions WHERE id=?',(identity,)).fetchone()
            if not row or row['state']!='approved':fail('Seuls les fichiers approuvés peuvent être récupérés.')
            path=self.directory/identity/('source'+Path(row['name']).suffix)
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest()!=row['sha256']:fail('Empreinte modifiée.')
            if not self.scanner and self.signature()!=row['scan_signature']:fail('Signatures modifiées : relancer l’analyse.')
            return data,'application/octet-stream'
