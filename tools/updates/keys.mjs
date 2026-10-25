import { generateKeyPairSync, createPublicKey } from 'node:crypto';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
export const privateKeyPath = () => process.env.BOUFBOWL_UPDATE_KEY || path.join(os.homedir(),'.config/boufbowl/update-signing.pem');
export async function prepareKey(root) {
  const target=path.join(root,'resources/update-key.json');
  const keyfile=privateKeyPath();
  let key=await fs.readFile(keyfile,'utf8').catch(()=>null);
  const pinned=JSON.parse(await fs.readFile(target,'utf8').catch(()=>'null'));
  if(!key) {
    if(pinned) throw new Error(`Release signing key missing: ${keyfile}. Restore the original key; do not rotate the trusted key to publish an update.`);
    key=generateKeyPairSync('ed25519').privateKey.export({type:'pkcs8',format:'pem'});
    await fs.mkdir(path.dirname(keyfile),{recursive:true,mode:0o700});
    await fs.writeFile(keyfile,key,{mode:0o600,flag:'wx'});
  }
  const publicKey=createPublicKey(key).export({type:'spki',format:'der'}).subarray(-32).toString('hex');
  if(pinned && pinned.public_key!==publicKey) throw new Error('Update signing key does not match resources/update-key.json');
  if(!pinned) await fs.writeFile(target,JSON.stringify({algorithm:'Ed25519',public_key:publicKey},null,2)+'\n');
  return key;
}
if(import.meta.main) { await prepareKey(path.resolve(import.meta.dir,'../..')); console.log('Update signing key ready (private key stored outside the repository).'); }
