"""Export source-specific element previews; Flash is never run in the website."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from tools.build_character_elements import symbols
from tools.character_element_catalog import inspect
from tools.site_portraits import webp_size


def find_preview(files,identity):
    # Sprite frames are all named 1.png; the parent identifies the actual symbol.
    sprites=[p for p in files if p.parent.name.startswith(f'DefineSprite_{identity}_') or p.parent.name==f'DefineSprite_{identity}']
    if sprites:return sprites[0]
    shapes=[p for p in files if p.parent.name=='shapes' and (p.stem.startswith(f'{identity}_') or p.stem==str(identity))]
    return shapes[0] if shapes else None


def export(root,catalog,jar=None,java=None,check=False,force=False):
    root=Path(root);destination=root/'assets/site/restoration/elements/previews';destination.mkdir(parents=True,exist_ok=True)
    cache=Path.home()/'.cache/boufbowl-flash-tools';jar=Path(jar or os.environ.get('FFDEC_JAR',cache/'ffdec-26.3.0/ffdec.jar')).resolve()
    homes=list((cache/'jdk-17').glob('jdk-*'));java=java or (str(homes[0]/'bin/java') if homes else 'java')
    wanted={}
    for entries in catalog['characters'].values():
        for entry in entries:wanted.setdefault(entry['source'],set()).add(entry['name'])
    cra=json.loads((destination.parent/'manifest.json').read_text())['elements'];all_previews={}
    for relative,selected in wanted.items():
        path=root/relative;key=hashlib.sha256(Path(__file__).read_bytes()+path.read_bytes()).hexdigest()
        record=destination/(path.stem+'-'+hashlib.sha256(relative.encode()).hexdigest()[:8]+'.json')
        previous=json.loads(record.read_text()) if record.is_file() else {}
        valid=not force and previous.get('fingerprint')==key and set(previous.get('previews',{}))==selected and all((root/e['image']).is_file() and hashlib.sha256((root/e['image']).read_bytes()).hexdigest()==e['sha256'] for e in previous['previews'].values())
        if valid:previews=previous['previews']
        elif check:raise ValueError('Character previews stale: '+relative)
        else:
            names,_=inspect(path);ids={name:identity for identity,name in names.items() if name in selected};previews={}
            if relative in ('assets/sprites/skins/11.swl','assets/sprites/skins/12.swl'):
                gender=1 if path.stem=='11' else 2
                previews={e['name']:{k:e[k] for k in ('image','width','height','sha256')} for e in cra if e['gender']==gender and e['name'] in selected}
            else:
                print(f'Exporting {len(ids)} native element previews: {relative}',flush=True)
                with tempfile.TemporaryDirectory(prefix='boufbowl-parts-') as temporary:
                    temporary=Path(temporary)
                    if path.suffix=='.swl':
                        flash,_=symbols(path);source=temporary/'source.swf';source.write_bytes(flash)
                    else:source=path
                    subprocess.run([java,'-Xmx1024m','-Djava.awt.headless=true','-jar',str(jar),'-select',','.join(f'{i}:1' for i in ids.values()),'-selectid',','.join(map(str,ids.values())),'-zoom','32' if path.suffix=='.swl' else '4','-format','shape:png','-exportTimeout','180','-export','sprite,shape',str(temporary/'export'),str(source)],check=True,timeout=210,stdout=subprocess.DEVNULL)
                    files=list((temporary/'export').rglob('*.png'))
                    def convert(item):
                        name,identity=item;candidate=find_preview(files,identity)
                        if candidate is None:raise ValueError(f'Missing preview {relative}#{name}')
                        output=destination/(hashlib.sha256((relative+'#'+name).encode()).hexdigest()[:20]+'.webp');staging=output.with_suffix('.building.webp')
                        subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-threads','1','-filter_threads','1','-i',str(candidate),'-vf','scale=768:768:force_original_aspect_ratio=decrease','-c:v','libwebp','-threads','1','-lossless','1',str(staging)],check=True,timeout=30)
                        width,height=webp_size(staging);staging.replace(output)
                        return name,{'image':output.relative_to(root).as_posix(),'width':width,'height':height,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
                    with ThreadPoolExecutor(max_workers=4) as pool:previews=dict(pool.map(convert,ids.items()))
            record.write_text(json.dumps({'fingerprint':key,'previews':previews},ensure_ascii=False)+'\n')
        all_previews[relative]=previews
    for entries in catalog['characters'].values():
        for entry in entries:entry.update(all_previews[entry['source']][entry['name']]);entry['status']='original'
    return catalog
