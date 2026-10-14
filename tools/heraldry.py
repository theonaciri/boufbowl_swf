"""Audit the original SWF's labeled blason artwork against available protocol IDs."""
import json
from pathlib import Path
import struct
import zlib

ROOT=Path(__file__).resolve().parent.parent
CLASSES={'SigilBackground':'com.ankamagames.boufbowl.ui.components.blason.BlasonBackgroundUI',
         'SigilCharge':'com.ankamagames.boufbowl.client.components.blason.BlasonIconUI'}


def tags(data,offset=0):
    while offset+2<=len(data):
        header=struct.unpack_from('<H',data,offset)[0];offset+=2
        length=header&63
        if length==63:length=struct.unpack_from('<I',data,offset)[0];offset+=4
        if offset+length>len(data):raise ValueError('Truncated SWF tag')
        yield header>>6,data[offset:offset+length]
        offset+=length
        if header>>6==0:break


def inventory(path=ROOT/'bin/boufbowl-client-1.9.6.swf'):
    raw=Path(path).read_bytes()
    if raw[:3] not in (b'CWS',b'FWS'):raise ValueError('Expected a compressed or uncompressed SWF')
    body=zlib.decompress(raw[8:]) if raw[:3]==b'CWS' else raw[8:]
    offset=((body[0]>>3)*4+12)//8+4
    symbols={};sprites={}
    for code,value in tags(body,offset):
        if code==39:sprites[struct.unpack_from('<H',value)[0]]=value
        elif code==76:
            count=struct.unpack_from('<H',value)[0];position=2
            for _ in range(count):
                identity=struct.unpack_from('<H',value,position)[0];position+=2
                end=value.index(0,position);symbols[value[position:end].decode()]=identity;position=end+1
    enums=json.loads((ROOT/'protocol/client_contract.json').read_text())['enums']
    result={}
    for kind,name in CLASSES.items():
        sprite=sprites[symbols[name]]
        labels=[value.split(b'\0')[0].decode() for code,value in tags(sprite,4) if code==43]
        if set(labels)!=set(enums[kind]):raise ValueError('Artwork/protocol mismatch for '+kind)
        result[kind]=[{'id':enums[kind][label],'frame':label} for label in labels]
    return result


if __name__=='__main__':
    print(json.dumps(inventory(),indent=2))
