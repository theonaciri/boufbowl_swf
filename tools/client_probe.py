"""Cached, disposable client instrumentation; production sources stay unchanged."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess

from tools.build_tools import ffdec_jar, java_binary
from tools.client_runtime_codegen import client_root_source
from tools.game_config import ROOT, flashvars_source, load_config, startup_source
from tools.package_cache import Inputs, Receipt, digest

ROOT_CLASS = 'com.ankamagames.boufbowl.BoufbowlClient'


def replace_once(source, marker, replacement):
    if source.count(marker) != 1:
        raise ValueError('Probe anchor changed: '+marker[:80])
    return source.replace(marker, replacement, 1)


def compile_probe(base, changes, root=ROOT):
    java, ffdec = java_binary(), ffdec_jar()
    inputs = Inputs()
    key = digest({'base': inputs.file(base), 'sources': changes,
                  'java': inputs.java(java), 'ffdec': inputs.file(ffdec)})
    directory = root/'.local/client-probes'/key
    output = directory/'client.swf'
    receipt = Receipt(root, 'client-probe/'+key)
    log = directory/'compile.log'
    if receipt.current(key, [output]):
        return output, True
    directory.mkdir(parents=True, exist_ok=True)
    replacements = []
    for index, (class_name, source) in enumerate(changes):
        patch = directory/f'{index}-{class_name.rsplit(".",1)[-1]}.as'
        patch.write_text(source)
        replacements.extend([class_name, str(patch)])
    temporary = directory/'client.building.swf'
    with log.open('w') as stream:
        result = subprocess.run([str(java), '-jar', str(ffdec), '-replace', str(base),
                                 str(temporary), *replacements], stdout=stream,
                                stderr=subprocess.STDOUT, timeout=600)
    if result.returncode:
        raise RuntimeError('Probe compilation failed; see '+str(log))
    temporary.replace(output)
    receipt.save(key, [output])
    return output, False


def probe_root(platform, native=False, root=ROOT):
    filename = root/('android/patches' if platform == 'android' else 'patches')/'BoufbowlClient.as'
    source = client_root_source(filename.read_text(), root)
    source = replace_once(source, '\n{', '\n{\n   import flash.utils.getDefinitionByName;\n   import flash.utils.setTimeout;')
    if native:
        marker = 'stage.frameRate = this.restoreFrameRate(preferences.data);'
        source = replace_once(source, marker, 'preferences.data.frameRateTarget = 30;\n         '+marker+
                              '\n         setTimeout(function():void { runSharedSmoke(true); },4000);')
    else:
        marker = 'this.initializeClientRuntime('+('false' if platform == 'android' else 'true')+');'
        source = replace_once(source, marker, marker+'''
         if(flash.external.ExternalInterface.available)
         {
            flash.external.ExternalInterface.addCallback("probeShared",function():Object {
               preferredFrameRate=30;stage.frameRate=30;return runSharedSmoke();
            });
            flash.external.ExternalInterface.addCallback("probeStats",function():Object {
               return {fps:stage.frameRate,ruffle:ruffleRuntime,preferred:preferredFrameRate};
            });
            var measuredEvents:Array = [];
            flash.external.ExternalInterface.addCallback("probeMeasurements",function(action:String):Object {
               if(action == "start") {
                  measuredEvents=[];setMeasurementActive(true);
                  setRuntimeMeasurementSink(function(sample:Object):void { measuredEvents.push(sample); });
                  setMeasurementPhase("3d");
               }
               if(action == "pause") setMeasurementActive(false);
               if(action == "resume") setMeasurementActive(true);
               if(action == "stop") {setMeasurementPhase("ui");setRuntimeMeasurementSink(null);}
               return {events:measuredEvents};
            });
         }''')
    position = source.rfind('   }')
    if position < 0:
        raise ValueError('Application root closing brace was not found')
    return source[:position]+(root/'tools/shared_client_smoke.as.inc').read_text()+\
        (root/'tools/shared_client_bench.as.inc').read_text()+source[position:]


def build_probe(platform='desktop', native=False, root=ROOT):
    base = root/'bin/boufbowl-client-1.9.6.swf'
    if native:
        config = load_config()
        startup = startup_source((root/'patches/StartUpApplicationCommand.as').read_text(), config, android=True)
        marker = 'private static function mockStatus(text:String, showToast:Boolean = false) : void\n      {'
        startup = replace_once(startup, marker, marker+'''
         trace("SHARED_SMOKE REPLAY fps=" + Stage(app.contextInjector.getInstance(Stage)).frameRate + " " + text);
         if(text.indexOf("ERROR:") == 0) setTimeout(function():void { Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit(1); },100);
         if(text.indexOf("Fixture delivered") == 0) setTimeout(function():void { trace("SHARED_SMOKE REPLAY PASS"); Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit(0); },1000);''')
        flashvars = flashvars_source((root/'patches/FlashVarsManager.as').read_text(), config)
        marker = '      public function getValue(param1:String) : String\n      {'
        flashvars = replace_once(flashvars, marker, marker+'\n         if(param1 == "mock" || param1 == "scene3d") return "1";\n         if(param1 == "server") return "0";')
        base, _ = compile_probe(base, [
            ('com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand', startup),
            ('com.ankamagames.xgaming.utils.flashvars.FlashVarsManager', flashvars),
            ('com.ankamagames.jerakine.resources.adapters.impl.SwlAdapter', (root/'android/patches/SwlAdapter.as').read_text())], root)
    return compile_probe(base, [(ROOT_CLASS, probe_root(platform, native, root))], root)


PROBE_PAGE = '''<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#171717}#game{width:640px;height:375px}</style>
<div id="game"></div><script src="/vendor/ruffle/ruffle.js"></script><script>
const query=new URLSearchParams(location.search);window.player=RufflePlayer.newest().createPlayer();
document.querySelector('#game').append(player);player.style.cssText='width:100%;height:100%';
player.ruffle().load({url:'/client-probe.swf',autoplay:'on',splashScreen:false,allowScriptAccess:true,quality:'low',unmuteOverlay:'hidden',
parameters:{lang:'fr',server:'0',mock:query.has('replay')?'1':'0',scene3d:'1',clientRuntime:query.get('runtime')||'ruffle',webFps:'30'}});
window.sharedSmoke=()=>player.ruffle().callExternalInterface('probeShared');
window.probeStats=()=>player.ruffle().callExternalInterface('probeStats');</script>'''


def serve_probe(client, fixture, port):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            route = self.path.split('?',1)[0]
            if route == '/probe.html':
                data = PROBE_PAGE.encode()
            elif route == '/client-probe.swf':
                data = client.read_bytes()
            elif route == '/resources/mock_match.json':
                data = fixture.read_bytes()
            elif route == '/__mock_trace':
                from urllib.parse import parse_qs, urlsplit
                with (client.parent/'replay.log').open('a') as stream:
                    stream.write(parse_qs(urlsplit(self.path).query).get('event',[''])[0]+'\n')
                self.send_response(204)
                self.end_headers()
                return
            else:
                return super().do_GET()
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    with ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(ROOT))) as server:
        print(json.dumps({'status':'serving','url':f'http://127.0.0.1:{port}/probe.html',
                          'replay_log':str(client.parent/'replay.log')}), flush=True)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', choices=('desktop','android'), default='desktop')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--port', type=int, default=9911)
    parser.add_argument('--fixture', type=Path, default=ROOT/'resources/mock_match.json')
    args = parser.parse_args()
    client, reused = build_probe(args.root)
    print(json.dumps({'status':'compiled','client':str(client),'reused':reused}), flush=True)
    if args.serve:
        serve_probe(client, args.fixture, args.port)


if __name__ == '__main__':
    main()
