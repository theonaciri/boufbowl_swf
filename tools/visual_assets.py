"""Prepare existing court atlases and compile editable customization colors."""
import json
from pathlib import Path
import re
import struct
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
NS = {'c':'http://www.collada.org/2005/11/COLLADASchema'}


def palettes():
    value=json.loads((ROOT/'resources/palettes.json').read_text())
    if any(len(p['colors'])>10 for p in value['club_palettes']):
        raise ValueError('Club palettes support at most 10 colors in the fixed editor layout')
    groups=[p['colors'] for p in value['club_palettes']]
    groups.extend(value['character_colors'].values())
    groups.extend(p[k] for p in value['character_palettes'] for k in ('hair','eyes','skin'))
    for colors in groups:
        if not colors or len(colors)>16 or any(not isinstance(c,str) or not re.fullmatch('[0-9a-fA-F]{6}',c) for c in colors):
            raise ValueError('Palette colors must be lists of 1–16 six-digit RGB hex values')
    for key in ('club_palettes','character_palettes'):
        ids=[p['id'] for p in value[key]]
        if any(not isinstance(i,int) or i<=0 for i in ids) or len(ids)!=len(set(ids)):
            raise ValueError('Palette IDs must be positive and unique')
    return value


def color_array(colors):
    return '['+','.join('Color3.fromRgbUInt(0x'+c+')' for c in colors)+']'


def palette_source(source):
    settings=palettes()
    for variable,key in (('colors',None),('hair','hair'),('eyes','eyes'),('skin','skin')):
        colors=settings['club_palettes'][0]['colors'] if key is None else settings['character_colors'][key]
        source,count=re.subn(r'var '+variable+r':Array = \[.*?\];',
                             'var '+variable+':Array = '+color_array(colors)+';',source,count=1)
        if count!=1: raise ValueError('Missing startup palette declaration: '+variable)
    clubs=[]
    for entry in settings['club_palettes']:
        colors=color_array(entry['colors'])
        clubs.append(f"clubPalettes.addItem({entry['id']},new ClubPaletteItem(1,0,{entry['id']},{colors},{colors},{colors}));")
    source,count=re.subn(r'clubPalettes.addItem\(1,new ClubPaletteItem\(1,0,1,colors,colors,colors\)\);','\n         '.join(clubs),source,count=1)
    if count!=1: raise ValueError('Missing club palette seed')
    extra=[]
    for entry in settings['character_palettes']:
        extra.append(f"palettes.addItem({entry['id']},new BoufbowlerPaletteItem(1,0,{entry['id']},0,0,{color_array(entry['hair'])},{color_array(entry['eyes'])},{color_array(entry['skin'])}));")
    source=source.replace('premium.updateCustomisationAssetsLists(', '\n         '.join(extra)+'\n         premium.updateCustomisationAssetsLists(',1)
    return source


def palette_translations(text):
    # Preserve the rest of the recovered language file, including its formatting.
    match=re.search(r'"boufbowler_palette_name_enum"\s*:\s*',text)
    if not match: raise ValueError('Missing character palette translations')
    start=match.end()
    value,length=json.JSONDecoder().raw_decode(text[start:])
    for entries in value.values():
        for palette in palettes()['character_palettes']:
            entries[str(palette['id'])]=palette['name']
    return text[:start]+json.dumps(value,ensure_ascii=False,indent=4)+text[start+length:]


def prepare_stadiums(root):
    root=Path(root)
    manifest=json.loads((root/'resources/stadium_art.json').read_text())
    template=root/manifest['template']
    paths={}
    for stadium,theme in manifest['stadiums'].items():
        if theme=='original':
            paths[stadium]='006_prairies/model.dae';continue
        art=manifest['textures'][theme]
        texture=root/art['path']
        data=texture.read_bytes()
        if data[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('Stadium textures must be PNG')
        width,height=struct.unpack('>II',data[16:24])
        x,y,w,h=art['region']
        if min(x,y)<0 or min(w,h)<=0 or x+w>width or y+h>height:
            raise ValueError('Stadium atlas region is outside the texture')
        path=root/f'assets/models/stadiums/theme_{theme}/model.dae'
        document=ET.parse(template)
        for image in document.findall('.//c:library_images/c:image',NS):
            init=image.find('c:init_from',NS)
            target=texture if image.get('id')=='terrain_jpg' else template.parent/init.text
            # Away3D 3.x stores one global texturePath. Mixed parent-directory
            # depths load the images but leave some materials unbound. Keep all
            # image URLs beneath the model's own directory on both platforms.
            image_path=path.parent/'images'/target.name
            image_path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,image_path)
            init.text='images/'+target.name
        # Away3D appends UV sources into a single table without rebasing face
        # indices. Modify only indices exclusively used by the ground triangles.
        mesh=document.find('.//c:geometry[@id="geom-colline"]/c:mesh',NS)
        triangles=mesh.find('c:triangles[@material="terrainjeu_1"]',NS)
        indices=set(map(int,triangles.find('c:p',NS).text.split()[2::3]))
        for other in mesh.findall('c:triangles',NS):
            if other is not triangles and indices & set(map(int,other.find('c:p',NS).text.split()[2::3])):
                raise ValueError('Ground UVs unexpectedly shared with scenery')
        values=mesh.find('c:source[@id="geom-colline-map1"]/c:float_array',NS)
        floats=list(map(float,values.text.split()))
        for uv_index in indices:
            index=uv_index*3
            floats[index]=(x+floats[index]*w)/width
            floats[index+1]=1-(y+h)/height+floats[index+1]*h/height
        values.text=' '.join(format(v,'.9g') for v in floats)
        path.parent.mkdir(parents=True,exist_ok=True)
        # Avoid namespace prefixes: the recovered Away3D parser expects the
        # document's original default COLLADA namespace.
        ET.register_namespace('',NS['c'])
        document.write(path,encoding='utf-8',xml_declaration=True)
        paths[stadium]=path.relative_to(root/'assets/models/stadiums').as_posix()
    return paths
