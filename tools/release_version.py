"""Shared semantic version, monotonic Android build and artifact provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

def release(root=ROOT):
    data=json.loads((Path(root)/'resources/release.json').read_text())
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',data['version']):
        raise ValueError('Use MAJOR.MINOR.PATCH in resources/release.json')
    if any(int(n)>999 for n in data['version'].split('.')) or not 1000000<data['android_build']<1000000000:
        raise ValueError('Version/build exceeds AIR limits or would downgrade the original Android app')
    return data

def android_descriptor(root=ROOT):
    data=release(root);build=data['android_build']
    internal=f'{build//1000000}.{build//1000%1000}.{build%1000}'
    source=(Path(root)/'android/application.xml').read_text()
    source=re.sub(r'<versionNumber>.*?</versionNumber>',f'<versionNumber>{internal}</versionNumber>',source)
    source=re.sub(r'<versionLabel>.*?</versionLabel>\s*','',source)
    return source.replace('</versionNumber>',f'</versionNumber>\n  <versionLabel>{data["version"]}</versionLabel>',1)

def record_artifact(path, root=ROOT):
    path=Path(path);data=release(root)
    path.with_suffix(path.suffix+'.release.json').write_text(json.dumps({**data,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size},indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('bump',choices=['patch','minor','major']);args=parser.parse_args()
    data=release();parts=list(map(int,data['version'].split('.')));index={'major':0,'minor':1,'patch':2}[args.bump]
    parts[index]+=1;parts[index+1:]=[0]*(2-index)
    data.update(version='.'.join(map(str,parts)),android_build=data['android_build']+1)
    (ROOT/'resources/release.json').write_text(json.dumps(data,indent=2)+'\n')
    (ROOT/'android/application.xml').write_text(android_descriptor())
    print(data['version'],f'(Android build {data["android_build"]})')
if __name__=='__main__':main()
