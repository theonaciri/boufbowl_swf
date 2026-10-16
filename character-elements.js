/* Original puppet parts, exported at build time; submissions remain quarantined. */
(async () => {
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const section=el('section');section.id='character-element-editor';section.className='section character-element-editor';
 section.append(el('span','ATELIER DES PANTINS'),el('h2','Un Crâ de référence. Une pièce à retrouver.'),el('p','Comparez un élément original Crâ avec la pièce à restaurer pour une autre classe ou un personnage. Les références montrent les formes originales, sans recoloration.'));
 const message=el('p','Ouverture du vestiaire…');message.setAttribute('role','status');section.append(message);
 document.querySelector('#asset-contributions').before(section);
 try {
  const [inventory,references]=await Promise.all(['assets/site/restoration/inventory.json','assets/site/restoration/elements/manifest.json'].map(async url=>{const r=await fetch(url);if(!r.ok)throw Error('Références indisponibles : relancer le build du site.');return r.json();}));
  const characters=inventory.characters.filter(c=>!c.body_available);if(!characters.length){message.textContent='Tous les corps recensés sont disponibles.';return;}
  const toolbar=el('div');toolbar.className='element-controls';
  function selector(label){const wrap=el('label',label),select=el('select');wrap.append(select);toolbar.append(wrap);return select;}
  const character=selector('Personnage / classe'),gender=selector('Référence Crâ'),search=el('input');search.type='search';search.placeholder='Rechercher : tête, cheveux, bras…';search.setAttribute('aria-label','Rechercher un élément');const searchLabel=el('label','Rechercher une pièce');searchLabel.append(search);toolbar.append(searchLabel);
  for(const c of characters){const option=el('option',`${c.name} · ${c.gender===1?'M':'F'}${c.hero?' · légende':''}`);option.value=c.id;character.append(option);}
  for(const [value,label] of [[1,'Crâ masculin'],[2,'Crâ féminin']]){const option=el('option',label);option.value=value;gender.append(option);}
  const element=selector('Élément original');
  const panels=el('div');panels.className='element-panels';const left=el('article'),right=el('article');
  left.append(el('h3','Référence originale'));const image=el('img');image.className='element-reference';const referenceName=el('p');const download=el('a','Télécharger la référence WebP ↧');left.append(image,referenceName,download);
  right.append(el('h3','Pièce à restaurer'));const target=el('h4'),description=el('p'),filename=el('code'),upload=el('div');
  right.append(target,description,filename,el('p','Format attendu : SWF vectoriel, 8 Mio maximum. Le nom du symbole Crâ sert de repère de travail ; il ne prouve pas que cette pièce existait à l’identique pour cette classe. Les morceaux proposés doivent être adaptés et assemblés avant de restaurer le corps complet.'),upload);
  const archive=el('div');right.append(el('p','Vous avez retrouvé le corps complet ? Envoyez plutôt son archive SWL d’origine.'),archive);
  panels.append(left,right);section.append(toolbar,panels);
  function populate(){
   const old=element.value;const query=search.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
   const rows=references.elements.filter(e=>String(e.gender)===gender.value&&e.name.toLowerCase().includes(query));
   const common=e=>/^(?:tete_(?:expression|triste)|colorGray_2_pupille|AnimStatique)/i.test(e.name);
   element.replaceChildren();
   for(const [label,shared] of [['Éléments propres au personnage',false],['Éléments communs · expressions et animations',true]]){
    const group=el('optgroup');group.label=label;
    for(const e of rows.filter(e=>common(e)===shared)){const option=el('option',e.name);option.value=e.name;group.append(option);}
    if(group.children.length)element.append(group);
   }
   if([...element.options].some(o=>o.value===old))element.value=old;render();
  }
  function render(){const c=characters.find(c=>c.id===character.value);const reference=references.elements.find(e=>e.name===element.value&&String(e.gender)===gender.value);upload.replaceChildren();archive.replaceChildren();
   if(!reference){image.hidden=true;download.hidden=true;referenceName.textContent='';description.textContent='';filename.textContent='';message.textContent='Aucun élément ne correspond à cette recherche. Essayez le nom technique : tete, cheveux, bras…';return;}
   message.textContent=`${element.options.length} éléments de référence · corps original ${c.name} ${c.gender===1?'M':'F'} manquant. Les contributions par pièce ne comptent pas comme un corps restauré.`;
   image.hidden=false;download.hidden=false;image.src=reference.image;image.alt=`${reference.name} — Crâ ${reference.gender===1?'M':'F'}`;referenceName.textContent=reference.name;download.href=reference.image;download.download=reference.image.split('/').pop();
   target.textContent=`${c.name} · ${c.gender===1?'masculin':'féminin'}`;description.textContent='Pièce demandée : '+reference.name;filename.textContent=reference.name+'.swf';
   if(Number(gender.value)!==c.gender){upload.append(el('p','Sélectionnez la référence du même sexe que le personnage pour proposer cette pièce.'));return;}
   const skin=c.body_path.split('/').pop().replace('.swl','');upload.append(AssetContributions.button(`assets/sprites/restoration-elements/${skin}/${reference.name}.swf`));archive.append(AssetContributions.button(c.body_path));
  }
  character.onchange=()=>{gender.value=String(characters.find(c=>c.id===character.value).gender);populate();};gender.onchange=populate;search.oninput=populate;element.onchange=render;
  gender.value=String(characters[0].gender);populate();
 }catch(error){message.textContent=error.message;}
})();
