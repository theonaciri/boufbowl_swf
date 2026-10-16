/* Public files go only to server quarantine; never into live assets. */
(() => {
  const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
  let items=[],selected=null,xhr=null;
  const status=el('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const dialog=el('dialog');dialog.className='asset-upload-dialog';
  const close=el('button','Fermer ×');close.type='button';close.className='asset-close';
  const title=el('h2','Une pièce retrouvée ?');const expected=el('p');
  const form=el('form');const label=el('label','Fichier original attendu');
  const input=el('input');input.type='file';input.required=true;label.append(input);
  const contactLabel=el('label','Comment vous recontacter ? (obligatoire)');
  const contact=el('input');contact.type='text';contact.name='contact';contact.required=true;contact.minLength=3;contact.maxLength=200;contact.autocomplete='off';contact.placeholder='Pseudo Discord, adresse e-mail ou autre moyen de contact';contact.className='asset-contact-input';
  const contactNote=el('small','Visible uniquement par les administrateurs pour échanger sur votre proposition. Effacé après 30 jours.');contactNote.id='asset-contact-note';contact.setAttribute('aria-describedby',contactNote.id);contactLabel.append(contact,contactNote);
  const consent=el('input');consent.type='checkbox';consent.required=true;
  const agreement=el('label');agreement.className='asset-consent';agreement.append(consent,document.createTextNode(' Je suis autorisé à transmettre ce fichier pour la restauration du jeu et son examen.'));
  const submit=el('button','Envoyer en quarantaine');submit.type='submit';submit.className='button';
  const cancel=el('button','Annuler l’envoi');cancel.type='button';cancel.hidden=true;
  const progress=el('progress');progress.max=100;progress.value=0;progress.hidden=true;
  const privacy=el('p','Aucun compte nécessaire. Votre contact et le fichier sont réservés aux administrateurs ; son format et son contenu sont contrôlés avant tout examen. Limites : 10 envois/heure, 30/jour, trois propositions en cours par ressource. Les fichiers en attente expirent après 14 jours.');
  privacy.className='workshop-small';const policy=el('a','Confidentialité');policy.href='confidentialite.html';privacy.append(' ',policy);
  form.append(label,contactLabel,agreement,submit,cancel,progress,status);dialog.append(close,title,expected,form,privacy);document.body.append(dialog);
  close.onclick=()=>{if(xhr)xhr.abort();dialog.close();};cancel.onclick=()=>xhr?.abort();
  dialog.addEventListener('cancel',()=>xhr?.abort());
  async function json(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'BoufbowlAssets'},body:JSON.stringify(body)});const data=await r.json();if(!data.ok)throw Error(data.error);return data;}
  const ready=fetch('api/asset-catalog',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{items=data.assets||[];render();}).catch(()=>{document.querySelector('#asset-catalog-status').textContent='Les envois nécessitent le serveur de jeu. Réessayez plus tard.';});
  async function open(path){await ready;selected=items.find(a=>a.path===path);if(!selected){status.textContent='Cette ressource ne reçoit pas de contribution actuellement.';dialog.showModal();return;}
    form.reset();submit.disabled=false;progress.hidden=true;status.textContent='';input.accept=selected.extension;
    expected.textContent=`${selected.related_to?.length?selected.related_to.map(r=>r.label).join(' · ')+' — ':''}Nom exact : ${selected.name} · ${selected.extension} · ${(selected.max_bytes/1048576).toLocaleString('fr-FR')} Mo maximum. ${selected.path}`;
    dialog.showModal();input.focus();}
  window.AssetContributions={button(path){const b=el('button','↥');b.type='button';b.title='Proposer ce fichier';b.setAttribute('aria-label','Proposer ce fichier');b.className='asset-upload-button';b.onclick=()=>open(path);return b;}};
  form.onsubmit=async event=>{event.preventDefault();const file=input.files[0];if(!selected||!file)return;
    if(file.name!==selected.name){status.textContent=`Le fichier doit porter exactement le nom ${selected.name}.`;return;}
    if(!file.size||file.size>selected.max_bytes){status.textContent='Le fichier dépasse la limite indiquée ou est vide.';return;}
    submit.disabled=true;status.textContent='Préparation de l’envoi…';
    try{const auth=await json('api/asset-token',{asset:selected.id,consent:consent.checked,contact:contact.value.trim()});
      await new Promise((resolve,reject)=>{xhr=new XMLHttpRequest();xhr.open('POST','api/asset-upload');xhr.timeout=125000;
        for(const [k,v] of Object.entries({'Content-Type':selected.mime,'X-Requested-With':'BoufbowlAssets','X-Asset-Id':selected.id,'X-Asset-Name':encodeURIComponent(file.name),'X-Asset-Token':auth.token}))xhr.setRequestHeader(k,v);
        progress.hidden=false;cancel.hidden=false;xhr.upload.onprogress=e=>{if(e.lengthComputable)progress.value=e.loaded/e.total*100;};
        xhr.onload=()=>{try{const data=JSON.parse(xhr.responseText);if(!data.ok)throw Error(data.error);status.textContent=`Merci ! Proposition ${data.id}. Le fichier attend son analyse et la validation d’un administrateur ; il ne remplace aucun asset automatiquement.`;resolve();}catch(error){reject(error);}};
        xhr.onerror=()=>reject(Error('Envoi interrompu.'));xhr.ontimeout=()=>reject(Error('Délai dépassé.'));xhr.onabort=()=>reject(Error('Envoi annulé.'));xhr.send(file);});
    }catch(error){status.textContent=error.message;}finally{xhr=null;submit.disabled=false;cancel.hidden=true;}};
  const section=el('section');section.id='asset-contributions';section.className='section asset-contributions';
  section.append(el('span','RECONSTITUONS LES ARCHIVES'),el('h2','Le vestiaire des pièces manquantes.'),el('p','Un original dort dans vos archives ? Proposez le fichier exact ci-dessous. Les propositions sont isolées, contrôlées puis examinées ; aucune publication automatique.'));
  const search=el('input');search.type='search';search.placeholder='Rechercher une classe, une légende, un stade ou un fichier';search.setAttribute('aria-label','Rechercher une ressource à restaurer');
  const count=el('p');count.id='asset-catalog-status';count.setAttribute('role','status');const list=el('div');list.className='asset-contribution-list';
  section.append(search,count,list);document.querySelector('#telecharger').before(section);search.oninput=render;
  const fold=value=>value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  function render(){const query=fold(search.value.trim());const rows=items.filter(a=>fold(a.path+' '+a.group+' '+(a.related_to||[]).map(r=>r.label).join(' ')).includes(query));count.textContent=`${rows.length} ressource(s) manquante(s), remplacée(s) ou de qualité réduite.`;list.replaceChildren();
    for(const a of rows){const row=el('div');row.className='asset-contribution-row';const copy=el('div');const context=el('span',(a.related_to||[]).map(r=>r.label).join(' · ')||'Aucune association renseignée');context.className='asset-context';copy.append(el('strong',a.name),context,el('small',a.path),el('span',a.status==='restored_low_quality'?'Restauré, qualité basse':a.status==='substitute'?'Original remplacé':'Fichier manquant'));row.append(copy,window.AssetContributions.button(a.path));list.append(row);}}
})();
