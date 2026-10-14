"""Class power text generated from the same frozen rules the worker uses."""
from copy import deepcopy
import json
import re

WORDS = {
    'fr': ('tous les alliés', 'tous les ennemis', 'PdV', 'portée (déplacement et passe)', "attaque", 'chaque élément', 'Changer de masque (classe, psychopathe ou pleutre).', 'pour ce tour', 'Un seul pouvoir par équipe et par tour. Le lanceur ne peut effectuer aucune autre action. Utilisations limitées par le stade.'),
    'en': ('all allies', 'all enemies', 'HP', 'range (movement and passing)', 'attack', 'each element', 'Change mask (Classic, Psychopath or Cowardly).', 'for this turn', 'One power per team per turn. The caster cannot perform any other action. Uses are limited by the stadium.'),
    'de': ('alle Verbündeten', 'alle Gegner', 'LP', 'Reichweite (Bewegung und Pass)', 'Angriff', 'jedes Element', 'Maske wechseln (Klasse, Berserker oder Hänsel).', 'für diese Runde', 'Eine Kraft pro Team und Runde. Der Anwender kann keine weitere Aktion ausführen. Das Stadion begrenzt die Anwendungen.'),
    'es': ('todos los aliados', 'todos los enemigos', 'PdV', 'alcance (movimiento y pase)', 'ataque', 'cada elemento', 'Cambiar de máscara (Zobal, Sáikopat o Eskérdikat).', 'durante este turno', 'Un poder por equipo y por turno. El lanzador no puede realizar ninguna otra acción. El estadio limita los usos.'),
}
ELEMENTS = {'fr': ['TERRE','FEU','AIR','EAU'], 'en':['EARTH','FIRE','AIR','WATER'], 'de':['ERDE','FEUER','LUFT','WASSER'], 'es':['TIERRA','FUEGO','AIRE','AGUA']}
NAMES = ('Cra','Ecaflip','Eniripsa','Enutrof','Feca','Iop','Osamodas','Pandawa','Rogue','Sacrier','Sadida','Sram','Xelor','Zobal')

def description(rule, language, constraints=True):
    allies,enemies,hp,reach,attack,each,mask,turn,limits=WORDS[language]
    def effect(elements, target):
        values = list(elements.values())
        if len(elements)==4 and len(set(values))==1:
            return f'{values[0]:+g} {each} → {target} ({turn})'
        return ', '.join(f'{amount:+g} {ELEMENTS[language][["TERRE","FEU","AIR","EAU"].index(element)]}' for element,amount in elements.items()) + f' → {target} ({turn})'
    if rule.get('change_mask'):
        text=mask
    elif 'enemy_chance' in rule:
        chance=rule['enemy_chance']*100
        text=f'{100-chance:g}%: '+effect(rule.get('elements',{}),allies)+f'; {chance:g}%: '+effect(rule.get('enemy_elements',{}),enemies)+'.'
    else:
        target=enemies if rule.get('target')=='enemies' else allies
        parts=[]
        if rule.get('hp',rule.get('heal',0)):
            parts.append(f'{rule.get("hp",rule.get("heal",0)):+g} {hp} → {target}')
        for key,label in [('range',reach),('attack',attack)]:
            if rule.get(key):parts.append(f'{rule[key]:+g} {label} → {target} ({turn})')
        elements=rule.get('elements') or ({rule['element']:rule['bonus']} if rule.get('element') else {})
        if elements: parts.append(effect(elements,target))
        text='; '.join(parts)+'.'
    return text+(' '+limits if constraints else '')

def client_abilities(rules):
    abilities=deepcopy(rules['abilities'])
    for rule in abilities.values():
        rule['descriptions']={lang:description(rule,lang) for lang in WORDS}
    return abilities

def update_translations(text, rules):
    for key in ('classes_order_tooltip_desc_enum','classes_order_combatlog_desc_enum'):
        translations={lang:{str(i):description(rules['abilities'][name],lang,key.endswith('tooltip_desc_enum')) for i,name in enumerate(NAMES,1)} for lang in WORDS}
        # The archive is JSON with comments/trailing commas; replace only the balanced block.
        start=re.search(r'"'+key+r'"\s*:\s*(?:/\*.*?\*/\s*)?\{',text,re.S)
        if not start:raise ValueError('Missing class power translation '+key)
        pos=start.end()-1; end=pos; depth=0; quoted=False; escaped=False
        for end in range(pos,len(text)):
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
        text=text[:pos]+json.dumps(translations,ensure_ascii=False,indent=4)+text[end+1:]
    return text
