"""Trace actual character-labelled Flash frames to their original element symbols."""
from collections import defaultdict
import json
from pathlib import Path
import re
import zlib
from tools.site_portraits import ROOT


def tags(data,offset=0):
    while offset+2<=len(data):
        value=int.from_bytes(data[offset:offset+2],'little');offset+=2;kind=value>>6;size=value&63
        if size==63:size=int.from_bytes(data[offset:offset+4],'little');offset+=4
        yield kind,data[offset:offset+size];offset+=size
        if kind==0:break


def inspect(path):
    data=path.read_bytes()
    if data[:2]==b'L\0':
        offset=10
        for _ in range(int.from_bytes(data[6:10],'big')):offset+=2+int.from_bytes(data[offset:offset+2],'big')
        data=data[offset:]
    body=zlib.decompress(data[8:]) if data[:3]==b'CWS' else data[8:]
    names={};sprites={}
    for kind,content in tags(body,(5+4*(body[0]>>3)+7)//8+4):
        if kind==76:
            pos=2
            for _ in range(int.from_bytes(content[:2],'little')):
                identity=int.from_bytes(content[pos:pos+2],'little');pos+=2;end=content.index(b'\0',pos)
                name=content[pos:end].decode();pos=end+1
                if re.fullmatch(r'[A-Za-z0-9_]+',name):names[identity]=name
        elif kind==39:sprites[int.from_bytes(content[:2],'little')]=list(tags(content,4))
    return names,sprites


def frames(timeline):
    depths={};label=None
    for kind,content in timeline:
        if kind==43:label=content.split(b'\0')[0].decode()
        elif kind in (26,70):
            flags=content[0];pos=1 if kind==26 else 2;depth=int.from_bytes(content[pos:pos+2],'little');pos+=2
            if kind==70 and (content[1]&8 or content[1]&16 and flags&2):pos=content.index(b'\0',pos)+1
            if flags&2:depths[depth]=int.from_bytes(content[pos:pos+2],'little')
        elif kind==28:depths.pop(int.from_bytes(content[:2],'little'),None)
        elif kind==1:yield label,set(depths.values())


def memberships(names,sprites):
    descendants={identity:set().union(*(ids for _,ids in frames(timeline))) for identity,timeline in sprites.items()}
    result=defaultdict(set)
    def visit(identity,seen):
        if identity in seen:return
        seen.add(identity)
        for child in descendants.get(identity,()):visit(child,seen)
    for identity,timeline in sprites.items():
        # Scenery/crowd color variants also use cg_ labels; only pose roots own character parts.
        if not re.fullmatch(r'boufbowler[12]_posing_?\d+',names.get(identity,'')):continue
        for label,ids in frames(timeline):
            if not label or not re.fullmatch(r'cg_\d+',label):continue
            seen=set()
            for identity in ids:visit(identity,seen)
            result[int(label[3:])].update(names[i] for i in seen if i in names)
    return result


def is_common(name,users):
    """Sharing a dependency is not enough: only generic anatomical parts qualify."""
    classes={identity//10 for identity in users if 10<=identity<500}
    if len(classes)<2:return False
    part=re.sub(r'^colorgray_\d+_','',name,flags=re.I)
    part=re.sub(r'^build\d+_','',part,flags=re.I)
    return bool(re.fullmatch(
        r'(?:tete_(?:expression\d+|triste)|pupille\d*|bras\d*|avantbras[DG]?\d*|avt_bras|'
        r'main[DG]?\d*|cou|collo\d*|braccio|epaule[DG]?\d*|torse|peau|jambe[DG]?\d*|jambes)'
        r'(?:_(?:[234][bB]?|[dfgFmM]|[DG]|\d+))*',part,re.I))


def loading_profile(character,root=ROOT):
    root=Path(root);patch=root/'patches/BoufbowlerSprite.as'
    code=patch.read_text()
    available=re.search(r'var available:Array = \[([^]]+)\]',code)
    hero=re.search(r'var heroAvailable:Boolean = (true|false)',code)
    if not available or not hero:raise ValueError('Audit the character loading policy before generating requirements')
    supported={int(i.strip()) for i in available[1].split(',')}
    requested=character['class_id']*10+character['gender']
    fallback=(bool(character['hero']) and hero[1]=='false') or requested not in supported
    rendered=character['gender']+10 if fallback else requested
    skins=[0,character['gender'],rendered]
    if character['hero'] and hero[1]=='true':skins.append(character['hero'])
    paths=[f'assets/sprites/skins/{i}.swl' for i in skins]
    return {'evidence':'patches/BoufbowlerSprite.as:buildEntity','runtime_archives':[{'path':p,'present':(root/p).is_file(),'replacement':fallback and p==paths[2]} for p in paths],
            'fallback':fallback,'rendered_skin':rendered,'original_archive':character['body_path'],'original_present':(root/character['body_path']).is_file(),
            'original_symbol_inventory_known':(root/character['body_path']).is_file(),'individual_symbol_requirements_known':False,'note':'Le client charge les archives entières. Un symbole contenu dans une archive n’est pas une dépendance individuelle prouvée du personnage.'}


def puppet_entries(characters,root=ROOT):
    """Only runtime skin libraries qualify, never illustration or pose libraries."""
    root=Path(root);class_names={};users=defaultdict(set)
    def parts(relative):
        path=root/relative
        if not path.is_file():return {}
        names,_=inspect(path)
        return {identity:name for identity,name in names.items() if not name.lower().startswith('anim')}
    for character in characters:
        names=parts(character['body_path']);class_names[character['id']]=names
        for name in names.values():users[name].add(character['hero'] or character['class_id']*10+character['gender'])
    specific={name for names in class_names.values() for name in names.values()}
    base='assets/sprites/skins/0.swl'
    # The default skin also embeds Cra placeholders; those are not common class originals.
    base_names=[name for name in parts(base).values() if name not in specific]
    result={}
    for character in characters:
        entries={name:{'name':name,'source':base,'kind':'body','scope':'shared','common':True} for name in base_names}
        relative=f"assets/sprites/skins/{character['gender']}.swl"
        for name in parts(relative).values():entries[name]={'name':name,'source':relative,'kind':'body','scope':'shared','common':True}
        for name in class_names[character['id']].values():entries[name]={'name':name,'source':character['body_path'],'kind':'body','scope':'class','common':is_common(name,users[name])}
        if not (root/character['body_path']).is_file():
            archive=Path(character['body_path']).name
            entries['archive:'+archive]={'name':archive,'source':character['body_path'],'kind':'archive','scope':'class','common':False,'status':'missing','evidence':'character-skin-archive','required_for_runtime':any(e['path']==character['body_path'] for e in loading_profile(character,root)['runtime_archives'])}
        result[character['id']]=list(entries.values())
    return result


def build(characters,root=ROOT,check=False,jar=None,java=None,force=False):
    root=Path(root)
    result={'characters':puppet_entries(characters,root),'notice':'Archives de chargement tirées de buildEntity. Aucun nom de pièce originale manquante n’est extrapolé depuis une autre classe. Les symboles retrouvés sont un inventaire de bibliothèque, pas des dépendances individuelles prouvées.'}
    from tools.export_character_previews import export
    missing={identity:[e for e in entries if e.get('status')=='missing'] for identity,entries in result['characters'].items()}
    result['characters']={identity:[e for e in entries if e.get('status')!='missing'] for identity,entries in result['characters'].items()}
    result=export(root,result,jar=jar,java=java,check=check,force=force)
    for identity,entries in missing.items():result['characters'][identity].extend(entries)
    from tools.character_asset_status import annotate
    result=annotate(result,characters,root,check=check)
    result['loading']={c['id']:loading_profile(c,root) for c in characters}
    result['scans']={}
    for character in characters:
        entries=result['characters'][character['id']]
        missing=[e for e in entries if e.get('status')=='missing' and not e.get('restored_image')]
        result['scans'][character['id']]={'name':character['name'],'gender':character['gender'],'archive':character['body_path'],'archive_present':(root/character['body_path']).is_file(),'known_class_symbols':len([e for e in entries if e['scope']=='class' and e['kind']=='body']),'missing':[{'name':e['name'],'source':e['source'],'evidence':e['evidence'],'kind':e['kind']} for e in missing],'restored':sum(bool(e.get('restored_image')) for e in entries),'quality_review':sum(e.get('target_status') in ('restored_low_quality','restored_unreviewed') for e in entries),'inventory_complete':(root/character['body_path']).is_file() and not missing}
    output=root/'assets/site/restoration/elements/characters.json'
    if check:
        if not output.is_file() or json.loads(output.read_text())!=result:raise ValueError('Character-specific element catalog is stale')
    else:
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
