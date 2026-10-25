import {test,expect} from 'bun:test';
import {generateKeyPairSync,verify} from 'node:crypto';
import {mkdtemp, mkdir,writeFile,rm} from 'node:fs/promises';
import os from 'node:os';import path from 'node:path';
import {releaseManifest} from './updates.mjs';import {newerRelease} from '../../client-updates.js';
test('compares versions numerically',()=>{expect(newerRelease('0.10.0','0.9.9')).toBe(true);expect(newerRelease('0.1.0','0.1.0')).toBe(false);expect(newerRelease('bad','0.1.0')).toBe(false)});
test('signs exact payload and advertises actual artifact versions only',async()=>{
 const root=await mkdtemp(path.join(os.tmpdir(),'boufbowl-updates-'));const old=process.env.BOUFBOWL_UPDATE_KEY;
 try {
  await mkdir(path.join(root,'resources'),{recursive:true});await mkdir(path.join(root,'android/build'),{recursive:true});
  const {privateKey,publicKey}=generateKeyPairSync('ed25519');const keyfile=path.join(root,'private.pem');
  await writeFile(keyfile,privateKey.export({type:'pkcs8',format:'pem'}));process.env.BOUFBOWL_UPDATE_KEY=keyfile;
  await writeFile(path.join(root,'resources/update-key.json'),JSON.stringify({public_key:publicKey.export({type:'spki',format:'der'}).subarray(-32).toString('hex')}));
  await writeFile(path.join(root,'resources/release.json'),JSON.stringify({version:'0.2.0',android_build:1000002}));
  const files=new Map([['downloads/Boufbowl Fan.apk',{sha256:'a'.repeat(64),bytes:30}]]);
  let envelope=JSON.parse(await releaseManifest(root,files,'https://example.com','revision'));
  expect(JSON.parse(envelope.payload).platforms.android).toBeUndefined();
  await writeFile(path.join(root,'android/build/Boufbowl Fan.apk.release.json'),JSON.stringify({version:'0.1.0',android_build:1000001,sha256:'a'.repeat(64),bytes:30}));
  envelope=JSON.parse(await releaseManifest(root,files,'https://example.com','revision'));
  expect(verify(null,Buffer.from(envelope.payload),publicKey,Buffer.from(envelope.signature,'base64'))).toBe(true);
  const payload=JSON.parse(envelope.payload);expect(payload.platforms.web.version).toBe('0.2.0');expect(payload.platforms.android.version).toBe('0.1.0');
  expect(verify(null,Buffer.from(envelope.payload+' '),publicKey,Buffer.from(envelope.signature,'base64'))).toBe(false);
 } finally {if(old===undefined)delete process.env.BOUFBOWL_UPDATE_KEY;else process.env.BOUFBOWL_UPDATE_KEY=old;await rm(root,{recursive:true,force:true})}
});
