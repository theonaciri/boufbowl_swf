"""Local tournament wording in all original languages, without external prizes."""
import json
import re


def replace_translation_block(text, key, value):
    """Replace one complete object, regardless of indentation or nested braces."""
    match = re.search(r'"' + re.escape(key) + r'"\s*:\s*\{', text)
    if not match:
        raise ValueError('Missing translation block: ' + key)
    start = match.end() - 1
    depth = 0
    comments = []
    tokens = r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|[{}]'
    for token in re.finditer(tokens, text[start:]):
        if token[0].startswith(('/*', '//')):
            comments.append(token[0])
        if token[0] == '{':
            depth += 1
        elif token[0] == '}':
            depth -= 1
            if depth == 0:
                block = json.dumps(value, ensure_ascii=False, indent=4)
                if comments:
                    block = '{\n' + '\n'.join(comments) + '\n' + block[2:]
                return text[:start] + block + text[start + token.end():]
    raise ValueError('Unclosed translation block: ' + key)


def update_tournament_text(text):
    labels={'en':'Local tournament','fr':'Tournoi local','de':'Lokales Turnier','es':'Torneo local'}
    remaining={'en':'Ends in $1','fr':'Fin dans $1','de':'Endet in $1','es':'Termina en $1'}
    blocks={'tournament_qualification_remaining':{'en':'Qualification ends in $1','fr':'Qualification : encore $1','de':'Qualifikation endet in $1','es':'Clasificación termina en $1'},
            'tournament_wait_round':{'en':'Wait for next round','fr':'Attendre le prochain tour','de':'Nächste Runde abwarten','es':'Espera próxima ronda'},
            'tournament_play_button_past':{'en':'Finished','fr':'Terminé','de':'Beendet','es':'Finalizado'},
            'tournament_time_remaining':remaining,
            'tournament_tournament_type_enum':{lang:{str(i):name for i in range(1,12)} for lang,name in labels.items()}}
    blocks['tournament_rewards_desc']={lang:{str(code):f'{g} G / {i} I / {c} C — '+{'en':'local currency','fr':'monnaie locale','de':'lokale Währung','es':'moneda local'}[lang]
        for code,(g,i,c) in enumerate(((20,10,10),(10,10,10),(0,5,10),(0,0,10)),1)} for lang in labels}
    for key,value in blocks.items():
        match=re.search(r'"'+key+r'"\s*:\s*\{',text)
        block=json.dumps(value,ensure_ascii=False,indent=4)
        if not match:
            at=text.rfind('}');text=text[:at].rstrip()+',\n    '+json.dumps(key)+': '+block+'\n'+text[at:];continue
        start=match.end()-1;depth=0;quoted=False;escaped=False
        for end in range(start,len(text)):
            ch=text[end]
            if quoted:
                if escaped:escaped=False
                elif ch=='\\':escaped=True
                elif ch=='"':quoted=False
            elif ch=='"':quoted=True
            elif ch=='{':depth+=1
            elif ch=='}':
                depth-=1
                if depth==0:break
        text=text[:start]+block+text[end+1:]
    return text
