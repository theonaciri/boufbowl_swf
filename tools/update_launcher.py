"""Cross-build the small standalone updater; discover/cache Go automatically."""
import hashlib,json,os,platform,shutil,subprocess,tarfile,tempfile
from pathlib import Path
from urllib.request import urlopen
from tools.package_cache import Inputs,Receipt,digest

def go_binary():
    found=shutil.which('go')
    if found:return Path(found)
    cache=Path.home()/'.cache/boufbowl-flash-tools/go'
    exe=cache/'go/bin/go'
    if exe.is_file():return exe
    machine={'aarch64':'arm64','arm64':'arm64','x86_64':'amd64','AMD64':'amd64'}.get(platform.machine())
    system={'Linux':'linux','Darwin':'darwin'}.get(platform.system())
    if not machine or not system:raise RuntimeError('Install Go and put go on PATH to build desktop updaters on this host')
    releases=json.load(urlopen('https://go.dev/dl/?mode=json',timeout=30));files=next(r['files'] for r in releases if r['stable'])
    item=next(x for x in files if x['os']==system and x['arch']==machine and x['kind']=='archive')
    cache.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as temp:
        package=Path(temp)/'go.tar.gz'
        with urlopen('https://go.dev/dl/'+item['filename'],timeout=120) as source,package.open('wb') as target:shutil.copyfileobj(source,target)
        if hashlib.sha256(package.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Go archive checksum mismatch')
        with tarfile.open(package) as archive:archive.extractall(temp,filter='data')
        try:shutil.move(str(Path(temp)/'go'),str(cache/'go'))
        except shutil.Error:
            if not exe.is_file():raise
    return exe

def build_updaters(root,platforms):
    root=Path(root);go=go_binary();key=json.loads((root/'resources/update-key.json').read_text())['public_key'];source=root/'tools/updates/updater.go'
    inputs=Inputs();result={}
    for target in platforms:
        output=root/'.local/updaters'/target/('BoufbowlUpdater.exe' if target=='windows' else 'BoufbowlUpdater')
        receipt=Receipt(root,'updater-'+target);identity=digest({'source':inputs.file(source),'go':inputs.file(go),'key':key,'target':target})
        if not receipt.current(identity,[output]):
            output.parent.mkdir(parents=True,exist_ok=True);temp=output.with_suffix('.building')
            env={**os.environ,'GOOS':'windows' if target=='windows' else 'linux','GOARCH':'386' if target=='windows' else 'amd64','CGO_ENABLED':'0','GOTOOLCHAIN':'local'}
            subprocess.run([str(go),'build','-trimpath','-ldflags',f'-s -w -X main.publicKey={key}','-o',str(temp),str(source)],env=env,check=True)
            temp.replace(output);receipt.save(identity,[output])
        result[target]=output
    return result
