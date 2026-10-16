"""Export original Cra puppet elements as WebP references; never generated artwork."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import zlib
from tools.site_portraits import ROOT


def symbols(path):
    data=path.read_bytes();offset=10
    for _ in range(int.from_bytes(data[6:10],'big')):
        length=int.from_bytes(data[offset:offset+2],'big');offset+=2+length
    flash=data[offset:];body=zlib.decompress(flash[8:]) if flash[:3]==b'CWS' else flash[8:]
    offset=(5+4*(body[0]>>3)+7)//8+4;result={}
    while offset+2<=len(body):
        value=int.from_bytes(body[offset:offset+2],'little');offset+=2;kind=value>>6;size=value&63
        if size==63:size=int.from_bytes(body[offset:offset+4],'little');offset+=4
        content=body[offset:offset+size];offset+=size
        if kind==76:
            pos=2
            for _ in range(int.from_bytes(content[:2],'little')):
                identity=int.from_bytes(content[pos:pos+2],'little');pos+=2;end=content.index(b'\0',pos)
                name=content[pos:end].decode();pos=end+1
                if re.fullmatch(r'[A-Za-z0-9_]+',name):result[name]=identity
        if kind==0:break
    return b'FWS'+flash[3:8]+body,result


def build(root=ROOT,jar=None,java=None,force=False,check=False):
    root=Path(root);destination=root/'assets/site/restoration/elements';manifest=destination/'manifest.json'
    sources=[root/f'assets/sprites/skins/{skin}.swl' for skin in (11,12)]
    fingerprint=hashlib.sha256(Path(__file__).read_bytes()+b''.join(p.read_bytes() for p in sources)).hexdigest()
    if not force and manifest.exists():
        previous=json.loads(manifest.read_text())
        if previous.get('fingerprint')==fingerprint and all((root/e['image']).is_file() and hashlib.sha256((root/e['image']).read_bytes()).hexdigest()==e.get('sha256') for e in previous['elements']):return previous
    if check:raise ValueError('Character element references require a website build')
    cache=Path.home()/'.cache/boufbowl-flash-tools'
    jar=Path(jar or os.environ.get('FFDEC_JAR',cache/'ffdec-26.3.0/ffdec.jar')).resolve()
    homes=list((cache/'jdk-17').glob('jdk-*'))
    java=java or (str(homes[0]/'bin/java') if homes else 'java')
    if not jar.is_file():raise ValueError('FFDec required to export character element references')
    destination.mkdir(parents=True,exist_ok=True);elements=[]
    for gender,path in enumerate(sources,1):
        flash,names=symbols(path)
        with tempfile.TemporaryDirectory(prefix='boufbowl-elements-') as temporary:
            temporary=Path(temporary);source=temporary/'source.swf';source.write_bytes(flash);ids=list(names.values())
            subprocess.run([java,'-Xmx512m','-Djava.awt.headless=true','-jar',str(jar),'-select',','.join(f'{i}:1' for i in ids),'-selectid',','.join(map(str,ids)),'-zoom','32','-exportTimeout','60','-export','sprite',str(temporary/'export'),str(source)],check=True,timeout=90,stdout=subprocess.DEVNULL)
            images=list((temporary/'export').rglob('*.png'))
            for name,identity in names.items():
                matches=[p for p in images if f'({name})' in str(p) or p.parent.name in (str(identity),f'DefineSprite_{identity}') or p.parent.name.startswith(f'DefineSprite_{identity}_')]
                if not matches:raise ValueError(f'No exported element for {gender}/{name}; files: {images[:2]}')
                output=destination/f'cra-{gender}-{name}.webp';staging=output.with_suffix('.building.webp')
                subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-threads','1','-filter_threads','1','-i',str(matches[0]),'-vf','scale=768:768:force_original_aspect_ratio=decrease','-c:v','libwebp','-threads','1','-lossless','1',str(staging)],check=True,timeout=15)
                from tools.site_portraits import webp_size
                width,height=webp_size(staging);staging.replace(output)
                elements.append({'gender':gender,'name':name,'symbol_id':identity,'image':output.relative_to(root).as_posix(),'width':width,'height':height,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
    data={'fingerprint':fingerprint,'elements':elements,'notice':'Éléments originaux Crâ : références de structure, sans recoloration.'}
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');return data


if __name__=='__main__':
    started=time.perf_counter();result=build();print(f"{len(result['elements'])} elements; Total execution time: {time.perf_counter()-started:.3f} s")
