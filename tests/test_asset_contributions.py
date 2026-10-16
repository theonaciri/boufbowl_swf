"""Filename allowlists, quarantine, real parsers, limits and authenticated review."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib
from backend.asset_contributions import AssetContributions, catalog
from backend.storage import ServiceError


def png():
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'+b'\xff\0\0'*2+b'\0'+b'\0\xff\0'*2))+chunk(b'IEND',b'')


class AssetContributionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'root';self.root.mkdir()
        self.manager=AssetContributions(self.root,Path(self.temp.name)/'private',scanner=lambda *_:'test-signature',start=False)
        self.item={'id':'asset','path':'assets/textures/missing.png','name':'missing.png','extension':'.png','max_bytes':1024*1024,'mime':'image/png'}
        self.mock=patch('backend.asset_contributions.catalog',return_value={'asset':self.item});self.mock.start()
    def tearDown(self):self.mock.stop();self.manager.close();self.temp.cleanup()
    def receive(self,data=None):
        data=png() if data is None else data
        token=self.manager.token('asset','127.0.0.1',True)['token']
        identity,path=self.manager.reserve('asset',token,'missing.png',len(data),'127.0.0.1');path.write_bytes(data);self.manager.finish(identity,path)
        return identity,path,token
    def state(self,identity):return self.manager.db.execute('SELECT state FROM submissions WHERE id=?',(identity,)).fetchone()[0]
    def test_element_catalog_targets_only_selected_character_and_missing_bodies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'assets/site/restoration/elements';folder.mkdir(parents=True)
            (folder/'characters.json').write_text(json.dumps({'characters':{'missing':[{'name':'tete_neutre','kind':'illustration','source':'assets/artworks/source.swf'}],'other':[{'name':'cheveux','kind':'illustration','source':'assets/artworks/source.swf'}]}}))
            (folder.parent/'inventory.json').write_text(json.dumps({'asset_status':[], 'characters':[
                {'id':'missing','body_available':False,'body_path':'assets/sprites/skins/21.swl','gender':1},
                {'id':'original','body_available':True,'body_path':'assets/sprites/skins/11.swl','gender':1}]}))
            self.mock.stop()
            try:
                from backend.asset_contributions import catalog as actual
                items=list(actual(root).values())
                installed=root/items[0]['path'];installed.parent.mkdir(parents=True);installed.write_bytes(b'installed')
                self.assertFalse(actual(root))
                data=json.loads((folder/'characters.json').read_text());data['characters']['missing'][0]['target_status']='restored_low_quality';(folder/'characters.json').write_text(json.dumps(data))
                self.assertEqual(next(iter(actual(root).values()))['status'],'restored_low_quality')
            finally:self.mock.start()
            self.assertEqual(len(items),1);self.assertEqual(items[0]['name'],'tete_neutre.swf')
            self.assertEqual(items[0]['character'],'missing');self.assertEqual(items[0]['group'],'character-elements')
    def test_exact_name_nonce_size_replay_and_ip_binding(self):
        with self.assertRaises(ServiceError):self.manager.token('asset','ip',False)
        with self.assertRaises(ServiceError):self.manager.token({},'ip',True)
        token=self.manager.token('asset','ip',True)['token']
        for name,size,ip in [('../missing.png',20,'ip'),('MISSING.PNG',20,'ip'),('missing.png',2**30,'ip'),('missing.png',20,'other')]:
            with self.subTest(name=name,size=size,ip=ip),self.assertRaises(ServiceError):self.manager.reserve('asset',token,name,size,ip)
        identity,path=self.manager.reserve('asset',token,'missing.png',20,'ip')
        with self.assertRaises(ServiceError):self.manager.reserve('asset',token,'missing.png',20,'ip')
        self.assertFalse((self.root/'assets/textures/missing.png').exists())
        self.manager.abort(identity)
    @unittest.skipUnless(shutil.which('bwrap') and shutil.which('ffmpeg'),'Sandboxed media tools required')
    def test_safe_preview_approval_immutable_original_and_rejection(self):
        identity,path,_=self.receive();self.manager.process(identity)
        self.assertEqual(self.state(identity),'pending')
        preview,mime=self.manager.preview(identity);self.assertEqual(mime,'image/png');self.assertTrue(preview.startswith(b'\x89PNG'))
        with self.assertRaises(ServiceError):self.manager.original(identity)
        self.manager.decision(identity,'approve','administrator')
        self.assertEqual(self.manager.original(identity)[0],png())
        self.assertFalse((self.root/self.item['path']).exists())
        path.write_bytes(b'changed')
        with self.assertRaises(ServiceError):self.manager.original(identity)
        self.manager.decision(identity,'reject','administrator')
        self.assertFalse(path.exists());self.assertEqual(self.state(identity),'rejected')
        with self.assertRaises(ServiceError):self.manager.preview(identity)
    def test_archive_removes_approved_bytes_and_preserves_decision(self):
        identity,path,_=self.receive();self.manager.process(identity)
        self.manager.decision(identity,'approve','administrator')
        self.manager.decision(identity,'archive','administrator')
        self.assertEqual(self.state(identity),'published');self.assertFalse(path.exists())
        self.assertEqual(self.manager.db.execute("SELECT action FROM decisions ORDER BY id DESC LIMIT 1").fetchone()[0],'archive')
        with self.assertRaises(ServiceError):self.manager.original(identity)
    def test_standalone_element_swf_has_static_main_frame_preview(self):
        if not (Path.home()/'.cache/boufbowl-flash-tools/ffdec-26.3.0/ffdec.jar').is_file():self.skipTest('FFDec unavailable')
        folder=Path(self.temp.name)/'standalone';folder.mkdir();path=folder/'source.swf'
        bits='01100'+''.join(format(n,'012b') for n in (0,2000,0,2000));bits+='0'*(-len(bits)%8)
        rect=int(bits,2).to_bytes(len(bits)//8,'big')
        body=rect+b'\0\x18\x01\0'+struct.pack('<H',9*64+3)+b'\x55\x88\xaa'+b'\x40\0\0\0'
        path.write_bytes(b'FWS\x09'+struct.pack('<I',len(body)+8)+body)
        metadata=self.manager.validate(path,folder,'assets/sprites/restoration-elements/21/tete.swf')
        self.assertEqual(metadata['thumbnails'],1);self.assertTrue((folder/'flash-0.png').read_bytes().startswith(b'\x89PNG'))
    def test_original_ankama_swl_static_preview(self):
        original=Path(__file__).resolve().parents[1]/'assets/sprites/skins/61.swl'
        if not original.exists():self.skipTest('Original skin unavailable')
        folder=Path(self.temp.name)/'skin';folder.mkdir();path=folder/'source.swl';path.write_bytes(original.read_bytes())
        metadata=self.manager.validate(path,folder,'assets/sprites/skins/61.swl')
        self.assertEqual(metadata['kind'],'flash');self.assertTrue(metadata['symbols'])
        self.assertGreater(metadata['tags'][39],0)
        if (Path.home()/'.cache/boufbowl-flash-tools/ffdec-26.3.0/ffdec.jar').is_file():
            self.assertGreater(metadata['thumbnails'],0)
    def test_malformed_or_infected_file_never_becomes_reviewable(self):
        identity,path,_=self.receive(b'<html>not a PNG</html>');self.manager.process(identity)
        self.assertEqual(self.state(identity),'blocked');self.assertFalse(path.exists())
        def infected(*_):raise ServiceError('ASSET_INFECTED','Antivirus test')
        self.manager.scanner=infected;identity,path,_=self.receive();self.manager.process(identity)
        self.assertEqual(self.state(identity),'blocked');self.assertFalse(path.exists())
        with self.assertRaises(ServiceError):self.manager.decision(identity,'approve','admin')
    def test_scanner_failure_fails_closed_and_rejects_path_traversal(self):
        def unavailable(*_):raise ServiceError('ASSET_SCANNER','Unavailable')
        self.manager.scanner=unavailable;identity,path,_=self.receive();self.manager.process(identity)
        self.assertEqual(self.state(identity),'scan_error');self.assertTrue(path.exists())
        with self.assertRaises(ServiceError):self.manager.preview(identity)
        with self.assertRaises(ServiceError):self.manager.decision(identity,'approve','admin')
        with self.assertRaises(ServiceError):self.manager.preview('../outside')
    def test_hourly_quota_and_hashed_network_identity(self):
        for _ in range(10):
            token=self.manager.token('asset','127.0.0.1',True)['token']
            identity,_=self.manager.reserve('asset',token,'missing.png',10,'127.0.0.1');self.manager.abort(identity)
        with self.assertRaises(ServiceError) as error:self.receive()
        self.assertEqual(error.exception.code,'ASSET_LIMIT')
        stored=self.manager.db.execute('SELECT ip FROM submissions LIMIT 1').fetchone()[0]
        self.assertEqual(len(stored),64);self.assertNotEqual(stored,'127.0.0.1')
    def test_flash_bounds_active_capabilities_and_xml_entities(self):
        folder=Path(self.temp.name)/'formats';folder.mkdir()
        body=b'\x08\0\0\x18\x01\0\x40\0\0\0'
        flash=folder/'source.swl';flash.write_bytes(b'L\0'+struct.pack('>II',25,1)+b'\0\4body'+b'FWS\x0a'+struct.pack('<I',len(body)+8)+body)
        meta=self.manager.validate(flash,folder,'assets/sprites/skins/12.swl');self.assertEqual(meta['kind'],'flash')
        flash.write_bytes(b'L\0'+struct.pack('>II',25,1)+b'\0\4body'+b'CWS\x0a'+struct.pack('<I',32)+zlib.compress(b'x'*1000000))
        with self.assertRaises(ServiceError):self.manager.validate(flash,folder,'assets/sprites/skins/12.swl')
        model=folder/'source.dae';model.write_bytes(b'<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///etc/passwd">]><COLLADA>&x;</COLLADA>')
        with self.assertRaises(ServiceError):self.manager.validate(model,folder,'assets/models/stadiums/test/model.dae')
        model.write_text('<COLLADA><image><init_from>https://evil.test/a.png</init_from></image></COLLADA>')
        with self.assertRaises(ServiceError):self.manager.validate(model,folder,'assets/models/stadiums/test/model.dae')


@unittest.skipUnless(shutil.which('clamscan') and Path('/var/lib/clamav/daily.cvd').exists(),'ClamAV definitions required')
class RealAntivirusTests(unittest.TestCase):
    def test_eicar_is_blocked_inside_networkless_sandbox(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'source.mp3'
            path.write_bytes(b'X5O!P%@AP[4\\PZX54(P^)7CC)7}'+b'$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')
            manager=AssetContributions(root,root/'private',start=False)
            try:
                with self.assertRaises(ServiceError) as error:manager.scan(path,root)
                self.assertEqual(error.exception.code,'ASSET_INFECTED')
            finally:manager.close()
