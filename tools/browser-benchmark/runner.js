const query=new URLSearchParams(location.search);
const player=RufflePlayer.newest().createPlayer();document.body.appendChild(player);
window.benchmarkPlayer=player;
window.benchmarkAPI=(name,...args)=>player.ruffle().callExternalInterface(name,...args);
const options=JSON.parse(query.get('option'));
await player.load({url:options.client || '/benchmark-client.swf',autoplay:'on',unmuteOverlay:'hidden',allowScriptAccess:true,quality:'high',scale:'showAll',forceScale:true,
 parameters:{lang:'fr',server:'0',mock:'0',scene3d:'1',clientRuntime:'ruffle',webFps:query.get('fps')}});
window.benchmarkLoaded=true;

document.addEventListener('pointerdown',()=>{for(const context of benchmarkContexts)context.resume();},true);
