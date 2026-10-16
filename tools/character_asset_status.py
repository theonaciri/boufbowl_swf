"""Explicit quality review for installed reconstructions; approval alone isn't restoration."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from backend.asset_contributions import AssetContributions
from tools.site_portraits import webp_size


def annotate(catalog,characters,root,check=False):
    root=Path(root);settings=root/'resources/asset-restorations.json'
    reviews=json.loads(settings.read_text()).get('assets',{}) if settings.is_file() else {}
    lookup={c['id']:c for c in characters};destination=root/'assets/site/restoration/elements/previews'
    generated={}
    for identity,entries in catalog['characters'].items():
        character=lookup[identity]
        skin=Path(character['body_path']).stem
        for entry in entries:
            if entry.get('scope')=='shared' or entry.get('kind')=='archive' or entry.get('status')!='missing':continue
            relative=f"assets/sprites/restoration-elements/{skin}/{entry['name']}.swf";path=root/relative
            entry['target_status']='missing'
            if not path.is_file():continue
            quality=reviews.get(relative,{}).get('quality')
            if quality not in (None,'good','low'):raise ValueError('Invalid restoration quality: '+relative)
            entry['target_status']={None:'restored_unreviewed','good':'restored_good','low':'restored_low_quality'}[quality]
            if relative in generated:entry['restored_image']=generated[relative];continue
            fingerprint=hashlib.sha256(path.read_bytes()+b'part-preview-1').hexdigest();output=destination/('restored-'+fingerprint[:24]+'.webp')
            if not output.is_file():
                if check:raise ValueError('Reconstruction preview missing: '+relative)
                with tempfile.TemporaryDirectory(prefix='boufbowl-restored-') as temporary:
                    folder=Path(temporary)
                    if not AssetContributions.flash_thumbnails(path,folder,[]):raise ValueError('Cannot preview reconstruction: '+relative)
                    staging=output.with_suffix('.building.webp')
                    subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-threads','1','-i',str(folder/'flash-0.png'),'-c:v','libwebp','-lossless','1',str(staging)],check=True,timeout=15)
                    webp_size(staging);staging.replace(output)
            generated[relative]=output.relative_to(root).as_posix();entry['restored_image']=generated[relative]
    return catalog
