"""Audit recovered files for the public restoration explorer; no completion guesses."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import zlib
from tools.site_portraits import POSES

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ['Crâ','Ecaflip','Eniripsa','Enutrof','Féca','Iop','Osamodas','Pandawa','Roublard','Sacrieur','Sadida','Sram','Xélor','Zobal']
SLUGS = ['cra','ecaflip','eniripsa','enutrof','feca','iop','osamodas','pandawa','roublard','sacrieur','sadida','sram','xelor','zobal']
STADIUM_NAMES = {'FARMSTEAD':'Cania','BRAKMAR':'Brâkmar','BONTA':'Bonta','BEACH':'La Plage','FRIGOST':'Frigost','KARA':'Kara','FOREST':'La Forêt','BALLOTIN':'Saint-Ballotin','PIXEL':'Pixel'}
HEROES = [(501,10,1),(502,9,2),(503,10,2),(504,12,1),(505,6,1),(506,11,2),(507,2,2),(508,1,2),(509,4,1),(510,3,2),(511,7,1),(512,3,1),(513,13,1),(514,8,1),(515,5,1),(516,12,1),(517,11,1),(518,14,1)]
LOW_QUALITY_RESTORATIONS = {f'music/music_resolution_loop_{i:02d}.mp3' for i in range(1,4)}
# Names of heroes beyond the first recovered team are read from the original catalog.


def homepage_assets(root):
    """Track supplied media and every literal homepage dependency, including missing ones."""
    root=Path(root)
    paths={'assets/site/restoration/class-'+str(i)+'.webp' for i in range(1,15)}
    paths.update(f'assets/site/restoration/grid-icons/{skin}.png' for skin in
                 [*(cls*10+gender for cls in range(1,15) for gender in (1,2)), *(h for h,_,_ in HEROES)])
    paths.update('assets/site/restoration/field-classes-'+str(i)+'.webp' for i in range(1,4))
    if not (root/'restoration.js').is_file():paths.clear()
    paths.update(p.relative_to(root).as_posix() for p in (root/'assets/site').rglob('*') if p.is_file() and p.suffix in ('.webp','.png','.svg','.mp4','.avif','.woff','.woff2'))
    for name in ('index.html','home.css','contributions.css','home.js','restoration.css','restoration.js'):
        source=(root/name).read_text() if (root/name).is_file() else ''
        paths.update(re.findall(r"assets/[A-Za-z0-9_./-]+\.(?:webp|png|svg|mp4|avif|woff2?)",source))
        if name=='home.js':
            block=source.split('const cinematicScenes = [',1)[-1].split('].map(',1)[0]
            version=re.search(r'const cinematicMediaVersion = "([a-z0-9-]+)"',source)
            suffix='-'+version.group(1) if version else ''
            extensions=('.mp4','.av1.mp4','.avif') if version else ('.webp','.mp4')
            for identity in re.findall(r'\[\s*"([a-z0-9-]+)"\s*,',block):
                paths.update('assets/site/cinematic-'+identity+suffix+extension for extension in extensions)
    return [{'path':path,'available':(root/path).is_file() and (root/path).stat().st_size>0 and (root/path).resolve().is_relative_to(root.resolve())} for path in sorted(paths) if not path.startswith('assets/site/responsive/')]

def audit(root=ROOT):
    root=Path(root)
    portrait_path=root/'assets/site/restoration/portraits.json'
    portrait_manifest=json.loads(portrait_path.read_text()) if portrait_path.is_file() else {}
    exists=lambda p:(root/p).is_file() and (root/p).stat().st_size>0 and (root/p).resolve().is_relative_to(root.resolve())
    sounds=json.loads((root/'resources/sound.json').read_text())
    stadium_config=json.loads((root/'resources/stadiums.json').read_text())['stadiums']
    art=json.loads((root/'resources/stadium_art.json').read_text())
    refs={v for v in sounds.values() if v}
    swf=root/'bin/boufbowl-client-1.9.6.swf'
    if swf.is_file():
        raw=swf.read_bytes();raw=zlib.decompress(raw[8:]) if raw[:3]==b'CWS' else raw[8:]
        refs.update(s.decode() for s in re.findall(rb'(?:interface|interactions|footsteps|ambient|tuto|music)/[A-Za-z0-9_/-]+\.mp3',raw))
    for cfg in stadium_config.values():
        refs.update(cfg.get('strategicMusics',[]));refs.update(cfg.get('resolutionMusics',[]))
        refs.update(v for k,v in cfg.items() if k in ('ambiantTrackName','publicHappySound') and v)
    actual={p.relative_to(root/'assets/sounds').as_posix() for p in (root/'assets/sounds').rglob('*.mp3')}
    def audio(path):
        return {'path':'assets/sounds/'+path,'file':path,'available':exists('assets/sounds/'+path),'referenced':path in refs,
                'category':path.split('/')[0],'aliases':[k for k,v in sounds.items() if v==path],
                'restored_low_quality':path in LOW_QUALITY_RESTORATIONS and exists('assets/sounds/'+path)}
    audio_files=[audio(p) for p in sorted(refs|actual) if not Path(p).is_absolute() and '..' not in Path(p).parts]
    def character(identity,cls,gender,hero=0,name=None):
        skin=hero or cls*10+gender;body='assets/sprites/skins/'+str(skin)+'.swl'
        poses={pose:'assets/site/restoration/'+identity+'-'+pose+'.webp' for pose in POSES}
        return {'id':identity,'class_id':cls,'class_name':CLASSES[cls-1],'name':name or CLASSES[cls-1],
            'gender':gender,'hero':hero,'icon':'assets/site/restoration/grid-icons/'+str(skin)+'.png',
            'body_available':exists(body),'body_path':body,'poses':{k:v for k,v in poses.items() if exists(v)},
            'palette_status':'review','illustration_archive_available':exists('assets/artworks/cutscene-boufbowler-repository.swf')}
    characters=[character(f'{slug}-{gender}',i,gender) for i,slug in enumerate(SLUGS,1) for gender in (1,2)]
    catalog=json.loads((root/'resources/offline_characters.json').read_text())
    hero_names={int(h['id']):h['name'] for h in catalog['special_characters']}
    lang=(root/'resources/lang.json').read_text() if (root/'resources/lang.json').is_file() else ''
    block=re.search(r'"unique_character_name_enum"\s*:\s*\{\s*"fr"\s*:\s*(\{[^}]+\})',lang)
    if block:hero_names.update({int(k):v for k,v in json.loads(block.group(1)).items()})
    characters += [character('hero-'+str(h),c,g,h,hero_names.get(h,'Personnage '+str(h))) for h,c,g in HEROES]
    stadiums=[]
    for key,cfg in stadium_config.items():
        theme=art['stadiums'][key];texture=art['textures'].get(theme,{})
        tracks=[]
        for role,paths in [('Tactique',cfg.get('strategicMusics',[])),('Résolution',cfg.get('resolutionMusics',[])),('Ambiance',[cfg.get('ambiantTrackName')])]:
            tracks += [{**audio(p),'role':role} for p in paths if p]
        stadiums.append({'id':key,'name':STADIUM_NAMES[key],'image':texture.get('web_path',texture.get('path')),
            'surface_available':bool(texture.get('path') and exists(texture['path'])),
            'original_geometry_available':key=='FARMSTEAD' and exists(art['template']),
            'model_path':'assets/models/stadiums/'+cfg['path'],'tracks':tracks})
    fx=[a for a in audio_files if a['category']!='music']
    asset_status = []
    def record(path, group, available, status=None):
        asset_status.append({'path':path, 'group':group, 'available':bool(available),
                             'status':status or ('found' if available else 'missing')})
    for c in characters:
        for pose in POSES:
            path='assets/site/restoration/'+c['id']+'-'+pose+'.webp'
            record(path, 'illustrations', exists(path))
        record(c['body_path'], 'bodies', c['body_available'])
    for stadium in stadiums:
        record(stadium['image'], 'surfaces', stadium['surface_available'])
        record(stadium['model_path'], 'geometry', stadium['original_geometry_available'],
               'found' if stadium['original_geometry_available'] else 'substitute' if exists(art['template']) else 'missing')
    for sound in audio_files:
        record(sound['path'], 'audio', sound['available'],
               'restored_low_quality' if sound['restored_low_quality'] else None)
    asset_groups = [
        {'label':'Illustrations recensées', 'found':sum(len(c['poses']) for c in characters), 'expected':len(POSES)*len(characters)},
        {'label':'Corps animés, légendes comprises', 'found':sum(c['body_available'] for c in characters), 'expected':len(characters)},
        {'label':'Fonds tactiques', 'found':sum(s['surface_available'] for s in stadiums), 'expected':len(stadiums)},
        {'label':'Décors 3D originaux', 'found':sum(s['original_geometry_available'] for s in stadiums), 'expected':len(stadiums)},
        {'label':'Audio, musiques comprises', 'found':sum(a['available'] for a in audio_files), 'expected':len(audio_files)},
    ]
    for group in asset_groups:
        group['missing']=group['expected']-group['found']
        group['completion_percent']=round(100*group['found']/group['expected'], 1) if group['expected'] else 0
    total_found=sum(g['found'] for g in asset_groups)
    total_expected=sum(g['expected'] for g in asset_groups)
    return {'version':1,'inventory_date':datetime.now(timezone.utc).date().isoformat(),
        'homepage_assets':homepage_assets(root),
        'scope':'Présence des fichiers référencés par les configurations et le client, complétée par les fichiers du dépôt. Un fichier retrouvé ne certifie ni sa fidélité ni son bon fonctionnement en jeu.',
        'characters':characters,'stadiums':stadiums,'audio':fx,'asset_groups':asset_groups,'asset_status':asset_status,
        'portrait_revision':portrait_manifest.get('revision',''),
        'portrait_export_count':len(portrait_manifest.get('exports',[])),
        'pose_labels':{key:value[0] for key,value in POSES.items()},
        'summary':{'completion_percent':round(100*total_found/total_expected, 1) if total_expected else 0,
                   'assets_missing':total_expected-total_found,
                   'audio_low_quality':sum(a['restored_low_quality'] for a in audio_files),
                   'assets_found':sum(g['found'] for g in asset_groups),'assets_expected':sum(g['expected'] for g in asset_groups),
            'bodies_found':sum(c['body_available'] for c in characters if not c['hero']),
            'bodies_expected':28,'geometry_found':sum(s['original_geometry_available'] for s in stadiums),
            'geometry_expected':len(stadiums),'audio_found':sum(a['available'] for a in audio_files),'audio_expected':len(audio_files)}}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=ROOT/'assets/site/restoration/inventory.json';content=json.dumps(audit(),ensure_ascii=False,indent=2)+'\n'
    if args.check:
        existing=json.loads(path.read_text()) if path.is_file() else None
        expected=json.loads(content)
        if existing:expected['inventory_date']=existing.get('inventory_date')
        if existing!=expected:raise SystemExit('Restoration inventory is stale; run python3 -m tools.build_restoration_data')
        print('Restoration inventory matches recovered files.')
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content);print('Built',path)
if __name__=='__main__':main()
