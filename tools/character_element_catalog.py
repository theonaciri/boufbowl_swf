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


def build(characters,root=ROOT,check=False,jar=None,java=None,force=False):
    root=Path(root);entries=defaultdict(list)
    for relative in ('assets/artworks/cutscene-boufbowler-repository.swf','assets/artworks/cutscene-illustration.swf'):
        names,sprites=inspect(root/relative);members=memberships(names,sprites);users=defaultdict(set)
        for identity,values in members.items():
            for name in values:users[name].add(identity)
        for character in characters:
            identity=character['hero'] or character['class_id']*10+character['gender']
            for name in sorted(members.get(identity,())):
                entries[character['id']].append({'name':name,'source':relative,'kind':'illustration','common':is_common(name,users[name])})
    body_users=defaultdict(set);body_names={}
    for character in characters:
        path=root/character['body_path']
        if path.is_file():
            names,_=inspect(path);body_names[character['id']]=names
            for name in names.values():body_users[name].add(character['hero'] or character['class_id']*10+character['gender'])
    for character in characters:
        path=root/character['body_path']
        if path.is_file():
            names=body_names[character['id']]
            entries[character['id']][0:0]=[{'name':name,'source':character['body_path'],'kind':'body','common':is_common(name,body_users[name])} for name in names.values()]
    result={'characters':dict(entries),'notice':'Appartenance extraite des images cg_<identité> et des dépendances de symboles ; illustrations et corps animés sont des sources distinctes.'}
    from tools.export_character_previews import export
    result=export(root,result,jar=jar,java=java,check=check,force=force)
    from tools.character_asset_status import annotate
    result=annotate(result,characters,root,check=check)
    output=root/'assets/site/restoration/elements/characters.json'
    if check:
        if not output.is_file() or json.loads(output.read_text())!=result:raise ValueError('Character-specific element catalog is stale')
    else:
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
