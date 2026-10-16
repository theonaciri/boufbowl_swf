/* Original puppet parts, exported at build time; submissions remain quarantined. */
(async () => {
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const section=el('section');section.id='character-element-editor';section.className='section character-element-editor';
 section.append(el('span','ATELIER DES PANTINS'),el('h2','Cinq originaux de référence. Une pièce à retrouver.'),el('p','Explorez uniquement les pièces utilisées par les pantins du jeu et comparez-les aux cinq corps originaux retrouvés. Les références montrent les formes originales, sans recoloration.'));
 const message=el('p','Ouverture du vestiaire…');message.setAttribute('role','status');section.append(message);
 document.querySelector('#asset-contributions').before(section);
 try {
  const [inventory,catalog]=await Promise.all(['assets/site/restoration/inventory.json','assets/site/restoration/elements/characters.json'].map(async url=>{const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('Références indisponibles : relancer le build du site.');return r.json();}));
  const characters=inventory.characters;if(!characters.length){message.textContent='Tous les corps recensés sont disponibles.';return;}
  const toolbar=el('div');toolbar.className='element-controls';
  function selector(label){const wrap=el('label',label),select=el('select');wrap.append(select);toolbar.append(wrap);return select;}
  const character=selector('Personnage / classe'),referenceCharacter=selector('Référence'),search=el('input');search.type='search';search.placeholder='Rechercher : tête, cheveux, bras…';search.setAttribute('aria-label','Rechercher un élément');const searchLabel=el('label','Rechercher une pièce');searchLabel.append(search);toolbar.append(searchLabel);
  for(const c of characters){const option=el('option',`${c.name} · ${c.gender===1?'M':'F'}${c.hero?' · légende':''}`);option.value=c.id;character.append(option);}
  const referenceCharacters=characters.filter(c=>c.body_available&&catalog.scans?.[c.id]?.inventory_complete!==false);
  for(const c of referenceCharacters){const option=el('option',`${c.name} · ${c.gender===1?'M':'F'} · 100 % disponible`);option.value=c.id;referenceCharacter.append(option);}
  const element=selector('Élément retrouvé / archive absente');let rows=[];
  const key=e=>e.source+'#'+e.name;
  function referenceFor(entry){const candidates=(catalog.characters[referenceCharacter.value]||[]).filter(e=>e.kind==='body'&&e.image);const exact=candidates.find(e=>e.name===entry.name);if(exact)return exact;const part=entry.name.match(/(?:cheveux|natte|pupille|visage|tete)/i)?.[0].toLowerCase();return part?candidates.find(e=>e.name.toLowerCase().includes(part)):null;}
  const panels=el('div');panels.className='element-panels';const left=el('article'),right=el('article');
  const referenceTitle=el('h3','Référence');const referenceHeading=el('div');referenceHeading.className='element-card-heading element-primary-heading';referenceHeading.append(referenceTitle);left.append(referenceHeading);const image=el('img');image.className='element-reference';const referenceName=el('p');const download=el('a','Télécharger la référence WebP ↧');left.append(image,referenceName,download);
  const heading=el('div');heading.className='element-card-heading element-primary-heading';const headingTitle=el('h3','Élément du personnage');headingTitle.title='Élément du personnage';const state=el('div');heading.append(headingTitle,state);right.append(heading);const ownImage=el('img');ownImage.className='element-reference character-own-preview';const missingPreview=el('div');missingPreview.className='element-missing-preview';missingPreview.append(el('span','?'),el('strong','Pièce du pantin à restaurer'));const ownDownload=el('a','Télécharger cet élément en WebP ↧');const sourceDownload=el('a','Télécharger l’archive originale ↧');sourceDownload.className='element-source-download';const bodyState=el('div');right.append(ownImage,missingPreview,ownDownload,sourceDownload);const target=el('h4'),description=el('p'),filename=el('code'),upload=el('div');
  const targetHeading=el('div');targetHeading.className='element-card-heading';targetHeading.append(target,bodyState);const bodyNote=el('p');right.append(targetHeading,bodyNote,description,filename,el('p','Seules les bibliothèques de pantins sont présentées. Les pièces communes du corps et les pièces spécifiques retrouvées sont distinguées. Les illustrations plein écran et les animations assemblées sont exclues.'),upload);
  const archive=el('div');right.append(el('p','Vous avez retrouvé le corps complet ? Envoyez plutôt son archive SWL d’origine.'),archive);
  const loading=el('section');loading.className='character-loading';panels.append(left,right);section.append(toolbar,loading,panels);
  function renderLoading(c){const profile=catalog.loading[c.id];loading.replaceChildren(el('h3','Archives de skin déclarées par le client'));for(const item of profile.runtime_archives){const line=el('p');line.append(el('code',item.path),document.createTextNode(item.replacement?' · REMPLACEMENT CRÂ':item.present?' · présent':' · fichier requis absent'));loading.append(line);}if(profile.fallback)loading.append(el('p','Le client actuel utilise un corps Crâ de remplacement. Les pièces de l’original ne sont pas connues ; elles ne sont pas déduites de ce remplacement.'));loading.append(el('small','Ce tableau décrit les skins du pantin standard ; les animations du squelette sont communes et dépendent des actions. Les symboles exportés ci-dessous ne sont pas des fichiers SWF à charger séparément.'));}
  const missingSection=el('section');missingSection.className='character-missing-inventory';const missingTitle=el('h3');const missingNote=el('p');const missingList=el('div');missingList.className='character-missing-list';missingSection.append(missingTitle,missingNote,missingList);section.append(missingSection);
  const report=el('a','Télécharger l’inventaire détaillé des 46 personnages ↧');report.href='assets/site/restoration/elements/characters.json';report.download='boufbowl-inventaire-personnages.json';missingSection.append(report);
  function renderMissing(c){const missing=(catalog.characters[c.id]||[]).filter(e=>e.status==='missing'&&!e.restored_image);missingTitle.textContent=`Archives originales manquantes · ${c.name} ${c.gender===1?'M':'F'} · ${missing.length}`;missingNote.textContent=missing.length?'Archives originales identifiées par le personnage. Leur absence peut être contournée actuellement par un remplacement Crâ ; aucun nom de pièce interne n’est supposé.':'Archive spécifique retrouvée. Les éventuelles dépendances internes non observées ne sont pas extrapolées.';missingList.replaceChildren();for(const entry of missing){const button=el('button');button.type='button';button.append(el('code',(entry.kind==='archive'?entry.name:entry.name+'.swf')),el('span','Manquant · examiner ↗'));button.setAttribute('aria-pressed',String(element.value===key(entry)));button.onclick=()=>{search.value='';populate();element.value=key(entry);render();panels.scrollIntoView({block:'start',behavior:'smooth'});};missingList.append(button);}}
  const legend=el('div');legend.className='element-state-legend';for(const status of ['original','restored_good','restored_low_quality','missing'])legend.append(badge(status));section.append(legend);
  function badge(status){const labels={original:['✦','ASSET ORIGINAL','Retrouvé dans les fichiers d’origine'],restored_good:['✓','RESTAURÉ · BONNE QUALITÉ','Reconstruction validée'],restored_low_quality:['!','RESTAURÉ · QUALITÉ BASSE','Une meilleure version est recherchée'],missing:['?','ASSET MANQUANT','À retrouver ou à reconstruire'],restored_unreviewed:['◷','RESTAURÉ · À VÉRIFIER','Qualité non encore évaluée']};const [icon,title,note]=labels[status]||labels.missing;const card=el('div');card.className='element-state element-state-'+status;const symbol=el('span',icon);symbol.className='element-state-symbol';symbol.setAttribute('aria-hidden','true');const copy=el('div');copy.append(el('strong',title),el('small',note));card.append(symbol,copy);return card;}
  function populate(){
   const old=element.value;const query=search.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
   const c=characters.find(c=>c.id===character.value);
   rows=(catalog.characters[c.id]||[]).filter(e=>e.name.toLowerCase().includes(query));
   element.replaceChildren();
   for(const [label,shared] of [['Éléments propres au personnage',false],['Éléments communs',true]]){
    const group=el('optgroup');group.label=label;
    for(const e of rows.filter(e=>e.common===shared)){const option=el('option',e.name+(e.status==='missing'?' · ARCHIVE ABSENTE':e.scope==='shared'?' · corps commun':' · corps original'));option.value=key(e);group.append(option);}
    if(group.children.length)element.append(group);
   }
   if([...element.options].some(o=>o.value===old))element.value=old;render();
  }
  function render(){
   const c=characters.find(c=>c.id===character.value);const entry=rows.find(e=>key(e)===element.value);upload.replaceChildren();archive.replaceChildren();
   renderMissing(c);renderLoading(c);
   target.textContent=`${c.name} · ${c.gender===1?'masculin':'féminin'}`;ownImage.hidden=true;missingPreview.hidden=true;ownDownload.hidden=true;sourceDownload.hidden=true;state.replaceChildren();bodyState.replaceChildren();bodyNote.hidden=true;
   if(!entry){image.hidden=true;download.hidden=true;referenceName.textContent='';description.textContent='';filename.textContent='';message.textContent='Aucun symbole retrouvé ne correspond à cette recherche pour ce personnage.';return;}
   const selectedReference=referenceCharacters.find(c=>c.id===referenceCharacter.value);
   const referenceLabel=selectedReference?`${selectedReference.name} ${selectedReference.gender===1?'M':'F'}`:'la référence';
   referenceTitle.textContent='Référence · '+referenceLabel;
   const reference=referenceFor(entry);
   state.append(badge(entry.restored_image?entry.target_status:entry.status||'original'));
   sourceDownload.href=entry.source;sourceDownload.download=entry.source.split('/').pop();sourceDownload.hidden=entry.status==='missing';missingPreview.hidden=entry.status!=='missing'||!!entry.restored_image;missingPreview.querySelector('strong').textContent=entry.kind==='archive'?'Archive originale absente · pièces internes inconnues':'Pièce du pantin à restaurer';
   const preview=entry.restored_image||(entry.image?entry.image+'?v='+entry.sha256.slice(0,16):null);
   if(preview){ownImage.src=preview;ownImage.alt=`${entry.name} — ${c.name} ${c.gender===1?'M':'F'}`;ownImage.hidden=false;ownDownload.href=preview;ownDownload.download=entry.name+'.webp';ownDownload.hidden=false;}
   if(!c.body_available||catalog.scans?.[c.id]?.missing.length){bodyState.append(badge('missing'));bodyNote.textContent='Les archives effectivement utilisées sont détaillées ci-dessus. L’inventaire interne de l’archive originale absente reste inconnu.';bodyNote.hidden=false;}
   message.textContent=`${element.options.length} symboles retrouvés ou archives absentes pour ${c.name} ${c.gender===1?'M':'F'} · ${c.body_available&&!catalog.scans?.[c.id]?.missing.length?'archive spécifique retrouvée':'archive originale absente ; pas de liste de pièces internes confirmée'}.`;
   image.hidden=!reference;download.hidden=!reference;
   if(reference){const url=reference.image+'?v='+reference.sha256.slice(0,16);image.src=url;image.alt=`${reference.name} — référence ${referenceLabel}`;referenceName.textContent=reference.name+(reference.name===entry.name?'':' · référence structurelle approximative, pas la pièce sélectionnée');download.href=url;download.download=referenceLabel.replaceAll(' ','-')+'-'+reference.name+'.webp';}
   else referenceName.textContent=`Aucun équivalent exporté pour ${referenceLabel} pour cet élément propre au personnage.`;
   description.textContent=`${entry.restored_image?'Pièce d’animation reconstruite':entry.status==='missing'?'Archive originale absente, contenu inconnu':entry.scope==='shared'?'Pièce commune du pantin retrouvée':'Pièce du corps original retrouvée'} : ${entry.name}`;filename.textContent=entry.kind==='archive'?entry.name:entry.name+' · symbole contenu dans une archive SWL';
   if(entry.kind==='archive'){upload.append(AssetContributions.button(entry.source));}else upload.append(el('p','Symbole retrouvé dans la bibliothèque indiquée. Sa présence ne prouve pas qu’il soit demandé individuellement au chargement.'));
   if(!c.body_available&&entry.kind!=='archive')archive.append(AssetContributions.button(c.body_path));else if(c.body_available)archive.append(el('p','Archive du corps original déjà retrouvée.'));
  }
  character.onchange=()=>{if(referenceCharacters.some(c=>c.id===character.value))referenceCharacter.value=character.value;populate();};referenceCharacter.onchange=render;search.oninput=populate;element.onchange=render;
  referenceCharacter.value=referenceCharacters[0]?.id||'';populate();
 }catch(error){message.textContent=error.message;}
})();
