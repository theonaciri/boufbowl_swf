import { createHash, createPrivateKey, createPublicKey, sign } from 'node:crypto';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { privateKeyPath } from '../updates/keys.mjs';

export async function releaseManifest(root, files, origin, revision, release) {
  const platforms={web:{version:release.version,revision,url:`${origin}/play.html`}};
  const artifacts={android:['android/build/Boufbowl Fan.apk','downloads/Boufbowl Fan.apk'],windows:['windows/build/Boufbowl Fan.exe','downloads/Boufbowl Fan.exe'],linux:['linux/build/Boufbowl Fan.run','downloads/Boufbowl Fan.run']};
  for(const [platform,[source,target]] of Object.entries(artifacts)) {
    const receipt=JSON.parse(await fs.readFile(path.join(root,source+'.release.json'),'utf8').catch(()=>'null'));
    const file=files.get(target);
    // Never advertise an old/unversioned package as the current release.
    if(receipt && file && receipt.sha256===file.sha256 && receipt.bytes===file.bytes) {
      platforms[platform]={version:receipt.version,sha256:file.sha256,bytes:file.bytes,url:`${origin}/${encodeURI(target)}?v=${file.sha256}`, ...(platform==='android'?{build:receipt.android_build}:{})};
    }
  }
  const payload=JSON.stringify({schema:1,version:release.version,platforms});
  const privateKey=await fs.readFile(privateKeyPath(),'utf8').catch(()=>null);
  let signature=null;
  if(privateKey) {
    const pinned=JSON.parse(await fs.readFile(path.join(root,'resources/update-key.json'),'utf8'));
    if(createPublicKey(privateKey).export({type:'spki',format:'der'}).subarray(-32).toString('hex')!==pinned.public_key) throw new Error('Update signing key does not match pinned release key');
    signature=sign(null,Buffer.from(payload),createPrivateKey(privateKey)).toString('base64');
  } else console.warn('Update signing key unavailable: desktop automatic updates will ignore this unsigned development manifest.');
  return JSON.stringify({payload,signature},null,2)+'\n';
}
