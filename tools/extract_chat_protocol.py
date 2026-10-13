"""Recover the separate original chat envelope and its union mappings."""
import json,re
from pathlib import Path
from tools import extract_protocol as parser
ROOT=Path(__file__).resolve().parent.parent
reference=ROOT.parent/'migration-work/scripts/scripts/com/ankamagames/xgaming/chat'
parser.REFERENCE=reference
messages={p.stem: m for p in sorted((reference/'protocol').rglob('*.as')) if (m:=parser.extract_message(p)) is not None}
union=(reference/'protocol/UnionProtocol.as').read_text()
ids=dict((name,int(value)) for name,value in re.findall(r'public static const (\w+):int = (\d+);',(reference/'protocol/ChatMessage/Type.as').read_text()))
payloads=dict(re.findall(r'case Type\.(\w+):\s*return param1\.(\w+);',union))
for message,name,field in re.findall(r'case "com\.ankamagames\.xgaming\.chat\.protocol::(\w+)":\s*_loc2_\.type = Type\.(\w+);\s*_loc2_\.(\w+) =',union):
    payloads[name]=field
fields={f['name']:f for f in messages['ChatMessage']['fields']}
network={name:{'id':ids[name],'payload':field,'message':fields[field]['message']} for name,field in payloads.items()}
(ROOT/'protocol/chat_contract.json').write_text(json.dumps({'messages':messages,'network':network,'enums':{}},indent=2)+'\n')
