import {ruleCalculator} from './rules-calculator-model.js';
const data=document.getElementById('rules-calculator-config');
if(data){
  const config=JSON.parse(data.textContent),model=ruleCalculator(config);
  const format=n=>new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2}).format(n);
  const colors=['#145da0','#985300','#7f2e72'];
  for(const panel of document.querySelectorAll('[data-calculator]')){
    const fields=Object.fromEntries([...panel.querySelectorAll('[data-setting]')].map(el=>[el.dataset.setting,el]));
    const initial=Object.fromEntries(Object.entries(fields).map(([key,el])=>[key,el.value]));
    const value=key=>Number(fields[key].value);
    function draw(changed){
      if(panel.dataset.calculator==='pickup' && value('air')+value('fire')>3){
        const other=changed==='fire'?'air':'fire';fields[other].value=3-value(changed==='fire'?'fire':'air');
      }
      for(const el of Object.values(fields)) if(el.type==='range') el.nextElementSibling.value=format(Number(el.value));
      let lines=[],maximum=30,minimum=0,xTitle='',yTitle='Échec (%)',result='',caption='';
      const stat=fields.stat?value('stat'):0;
      switch(panel.dataset.calculator){
        case 'pass':{
          maximum=Number(fields.distance.max);xTitle='Distance (cases)';
          lines=[1,2,3].map(orders=>({name:`${orders} ordre(s) Air`,fn:d=>model.throwFailure(stat,orders,d)}));
          result=lines.map((line,i)=>`${i+1} Air : ${line.fn(value('distance'))===null?'hors portée, lancer en attente':format(line.fn(value('distance')))+' % d’échec'} (portée ${format(model.range(i+1))} cases)`).join(' ; ');
          caption=`À ${format(value('distance'))} cases. Chaque couleur correspond à un nombre d’ordres Air ; hors portée, le tracé passe à 100 % si les lancers courts sont activés.`;
          break;
        }
        case 'catch':{
          xTitle=fields.mode.value==='intercept' && config.simulation.ball.interception_uses_fire_stat?'Caractéristique Feu':'Caractéristique Air';
          const intercept=fields.mode.value==='intercept';
          lines=[1,2,3].map(orders=>({name:`${orders} ordre(s) ${intercept?'Feu':'Air'}`,fn:stat=>model.catchFailure(stat,orders,intercept)}));
          result=lines.map((line,i)=>`${i+1} ordre(s) : ${format(line.fn(stat))} % d’échec`).join(' ; ');
          caption=`Pour une caractéristique de ${format(stat)}. Les chances sont conditionnelles à la possibilité de tenter l’action.`;break;
        }
        case 'pickup':{
          maximum=9;xTitle='Autres joueurs proches';
          lines=[{name:'Échec du ramassage',fn:nearby=>model.pickupFailure(stat,value('air'),value('fire'),nearby,value('losses'))}];
          result=`${format(lines[0].fn(value('nearby')))} % d’échec par tentative ; ${value('air')+value('fire')} ordre(s) disponible(s).`;
          caption='Alliés et adversaires comptent de la même manière. Sans ordre Air ou Feu, aucun ramassage ne peut être tenté.';break;
        }
        case 'movement':{
          const orders=fields.allocation.value.split(',').map(Number),range=model.movement(stat,orders,0);
          maximum=range.maximum;xTitle='Éloignement (cases)';yTitle='Risque de chute (%)';
          lines=[{name:'Risque du déplacement',fn:d=>model.movement(stat,orders,d).failure}];
          result=`Référence : ${format(range.safe)} cases ; maximum : ${format(maximum)} cases ; risque à la référence : ${format(model.movement(stat,orders,range.safe).failure)} % ; au maximum : ${format(lines[0].fn(maximum))} %.`;
          caption='Sans déplacement : 0 %. La zone au-delà du maximum est inaccessible. Un seul tirage est utilisé sur le parcours.';break;
        }
        case 'stun':
          xTitle='Caractéristique Eau';yTitle='Durée (secondes)';
          lines=[{name:'Étourdissement',fn:model.stun}];
          result=`Avec ${format(stat)} Eau : ${format(model.stun(stat))} seconde(s) de temps simulé.`;
          caption='La durée est arrondie au pas de simulation supérieur. Elle ne décrit pas le temps nécessaire pour se relever après une mise au sol.';break;
        case 'combat':
          minimum=-30;maximum=30;xTitle='Écart de score avant tirage';yTitle='Victoire (%)';
          lines=[{name:'Probabilité de victoire',fn:model.combat}];
          result=model.combat(value('margin'))===null?'Aucun tirage logistique dans ce profil.':`${format(model.combat(value('margin')))} % de victoire pour un écart de ${format(value('margin'))}.`;
          caption=config.simulation.rulebook.combat.random_score?'Score d’attaque moins score de défense, avant le bruit. À écart nul : 50 %. Cette approximation ne certifie pas l’équilibrage historique.':'Le profil actuel ne comporte pas de tirage logistique : aucune courbe de probabilité n’est tracée.';break;
      }
      panel.querySelector('figure').hidden=false;
      const svg=panel.querySelector('svg'),width=Math.max(290,panel.querySelector('figure').clientWidth),left=48,right=width-12,top=27,bottom=207;
      svg.setAttribute('viewBox',`0 0 ${width} 250`);
      const samples=Array.from({length:161},(_,i)=>minimum+(maximum-minimum)*i/160);
      const ceiling=panel.dataset.calculator==='stun'?Math.max(1,model.stun(0)):100;
      const X=x=>left+(x-minimum)/(maximum-minimum||1)*(right-left),Y=y=>bottom-y/ceiling*(bottom-top);
      const ns='http://www.w3.org/2000/svg';svg.replaceChildren();
      const element=(tag,attrs,text)=>{const el=document.createElementNS(ns,tag);for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;};
      element('title',{},`${yTitle} selon ${xTitle.toLowerCase()}`);
      for(let i=0;i<=4;i++){
        const y=ceiling*i/4; element('line',{x1:left,x2:right,y1:Y(y),y2:Y(y),stroke:'#d2c8b1'});
        element('text',{x:left-9,y:Y(y)+4,'text-anchor':'end'},format(y));
        const x=minimum+(maximum-minimum)*i/4;element('text',{x:X(x),y:226,'text-anchor':'middle'},format(x));
      }
      element('text',{x:left,y:15},yTitle);element('text',{x:right,y:246,'text-anchor':'end'},xTitle);
      lines.forEach((line,index)=>{
        let path='',gap=true;for(const x of samples){const y=line.fn(x);if(y===null){gap=true;continue;}path+=`${gap?'M':'L'}${X(x).toFixed(2)},${Y(y).toFixed(2)} `;gap=false;}
        element('path',{d:path,fill:'none',stroke:colors[index],'stroke-width':2.5,...(index===1?{'stroke-dasharray':'8 3'}:index===2?{'stroke-dasharray':'2 3'}:{})});
      });
      const selected=fields.distance?value('distance'):fields.margin?value('margin'):fields.nearby?value('nearby'):panel.dataset.calculator==='movement'?null:stat;
      if(selected!==null){
        element('line',{x1:X(selected),x2:X(selected),y1:top,y2:bottom,stroke:'#606a60','stroke-dasharray':'4 4'});
        lines.forEach((line,index)=>{const y=line.fn(selected);if(y!==null)element('circle',{cx:X(selected),cy:Y(y),r:4,fill:colors[index]});});
      }
      panel.querySelector('figcaption').textContent=lines.map(line=>line.name).join(' · ')+' — '+caption;
      let legend=panel.querySelector('.rule-chart-legend');
      if(!legend){legend=document.createElement('div');legend.className='rule-chart-legend';panel.querySelector('figcaption').before(legend);}
      legend.replaceChildren(...lines.map((line,index)=>{const item=document.createElement('span');item.style.color=colors[index];item.textContent=['━ ','┄ ','┈ '][index]+line.name;return item;}));
      panel.querySelector('.rule-readout').textContent=result;
    }
    panel.addEventListener('input',event=>draw(event.target.dataset.setting));
    panel.querySelector('.rule-reset').addEventListener('click',()=>{for(const [key,setting] of Object.entries(initial))fields[key].value=setting;draw();});
    panel.addEventListener('toggle',()=>{if(panel.open)draw();});
  }
}
