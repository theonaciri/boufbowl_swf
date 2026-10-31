"""Build an isolated rendering benchmark and serve its browser controls (no backend/accounts)."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from urllib.parse import unquote, urlsplit
from pathlib import Path

from tools.client_probe import compile_probe, ROOT
from tools.client_runtime_codegen import client_root_source
from tools.game_config import load_config, startup_source
from tools.build_mock_fixture import build_fixture
from tools.flash_protocol import Codec


def create_fixture():
    fixture = build_fixture()
    # All ten actors run the same deterministic zigzag for forty game seconds.
    scenario = fixture['steps'][2]['decoded']
    for track in scenario['boufbowlerTracks']:
        initial = track['item'][0]['movement']['positions'][0]
        near = dict(initial, x=-initial['x'])
        track['item'][0]['movement'] = {'positions': [dict(initial) if n % 2 == 0 else dict(near) for n in range(65)], 'startTick': 0, 'endTick': 800}
    scenario['turnEndTick'] = 800
    fixture['steps'][2]['hex'] = Codec().envelope('RESOLUTION_SCENARIO', scenario).hex()
    # Menu/orders timing is driven from the browser, not a racing timeout.
    fixture['steps'][2]['after_ms'] = 3600000
    fixture['steps'] = fixture['steps'][:4]
    # Final positions match the zigzags' return to their initial positions.
    final = fixture['steps'][3]
    final['decoded'] = json.loads(json.dumps(fixture['steps'][1]['decoded']))
    final['decoded']['teamState']['turn'] = 2
    final['hex'] = Codec().envelope('FIELD_STATE', final['decoded']).hex()
    fixture['name'] = 'Browser benchmark: ten actors, Cania, fixed zigzag'
    return fixture


def build():
    if not (ROOT / 'bin/boufbowl-client-1.9.6.swf').is_file():
        raise SystemExit('Build the game first: bun run build')
    output = ROOT / '.local/browser-benchmark'
    output.mkdir(parents=True, exist_ok=True)
    fixture = create_fixture()
    data = json.dumps(fixture, sort_keys=True).encode()
    (output / 'fixture.json').write_bytes(data)

    source = client_root_source((ROOT / 'patches/BoufbowlClient.as').read_text())
    imports = ['flash.display.DisplayObject', 'flash.display.DisplayObjectContainer', 'flash.utils.getQualifiedClassName',
               'as3.collections.ArrayList', 'as3.collections.iterators.IIterator', 'com.ankamagames.xgaming.utils.math.geom.Point3', 'com.netease.protobuf.Int64',
               'com.ankamagames.boufbowl.resolution.display.script.runner.SceneController',
               'com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand']
    for name in imports:
        source = source.replace('   import ', f'   import {name};\n   import ', 1)
    anchor = 'this.initializeClientRuntime(true);'
    assert source.count(anchor) == 1
    source = source.replace(anchor, anchor + '''
         flash.external.ExternalInterface.addCallback("benchmarkViewScale",function(scale:Number):Object {
            if(isNaN(scale) || scale < 1 || scale > 8) throw new Error("Benchmark scale must be1..8");
            _wheelGameView.scaleX = scale;_wheelGameView.scaleY = scale;
            _wheelGameView.x = stage.stageWidth*(1-scale)/2;_wheelGameView.y = stage.stageHeight*(1-scale)/2;
            return {scale:_wheelGameView.scaleX,x:_wheelGameView.x,y:_wheelGameView.y};
         });
         flash.external.ExternalInterface.addCallback("benchmarkSample",benchmarkSample);
         flash.external.ExternalInterface.addCallback("benchmarkPositions",benchmarkPositions);
         flash.external.ExternalInterface.addCallback("benchmarkState",benchmarkState);
         flash.external.ExternalInterface.addCallback("benchmarkStart",StartUpApplicationCommand.benchmarkStart);
         flash.external.ExternalInterface.addCallback("benchmarkResolve",StartUpApplicationCommand.benchmarkResolve);
         flash.external.ExternalInterface.addCallback("benchmarkCutscene",benchmarkCutscene);
         flash.external.ExternalInterface.addCallback("benchmarkCutsceneStatus",function():Boolean { return benchmarkCutsceneDone; });
         flash.external.ExternalInterface.addCallback("benchmarkFinish",function():void { SceneController.active.pauseGame(32); });
''')
    position = source.rfind('   }')
    source = source[:position] + (ROOT / 'tools/browser-benchmark/probe.as.inc').read_text() + source[position:]
    startup = startup_source((ROOT / 'patches/StartUpApplicationCommand.as').read_text(), load_config())
    startup = startup.replace('"../resources/mock_match.json"', '"/benchmark-fixture.json"')
    startup = startup.replace('90000/Math.min(1,replaySpeed)', '300000/Math.min(1,replaySpeed)')
    # No localhost trace HTTP requests in measured intervals.
    startup = startup.replace('if("../__mock_trace" != "")', 'if(false)')
    marker = 'private static function mockStatus(text:String, showToast:Boolean = false) : void\n      {'
    assert startup.count(marker) == 1
    startup = startup.replace(marker, marker + '\n         flash.external.ExternalInterface.call("benchmarkNotice",text);')
    pos = startup.rfind('   }')
    startup = startup[:pos] + '''
      public static function benchmarkStart() : void { startMock(); }
      public static function benchmarkResolve() : void { clearTimeout(mockTimer);deliverMockStep(); }
''' + startup[pos:]
    changes = [('com.ankamagames.boufbowl.BoufbowlClient', source),
               ('com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand', startup)]
    # Build only touched overrides; do not replace production clients/packages.
    probe_changes = []
    actor = (ROOT / 'patches/Boufbowler.as').read_text()
    actor = actor.replace('   import ', '   import flash.external.ExternalInterface;\n   import ', 1)
    actor = actor.replace('      private var _uid:uint;', '      private var _uid:uint;\n      private var benchmarkMoved:Boolean = false;')
    marker = 'this._trajectory = new SegmentTrajectory(this.position,destination,gameTime,gameTime + duration);'
    assert actor.count(marker) == 1
    actor = actor.replace(marker, marker + '''
         if(!benchmarkMoved) { benchmarkMoved=true;ExternalInterface.call("benchmarkNotice","Actor moving "+this._uid); }
''')
    probe_changes.append(('com.ankamagames.boufbowl.resolution.display.model.Boufbowler', actor))
    probe_changes.append(('com.ankamagames.boufbowl.client.match.controller.ChooseMusicCommand',
                          (ROOT / 'tools/browser-benchmark/ChooseMusicCommand.as').read_text()))
    print('Preparing cached scene instrumentation…', flush=True)
    probe_base, _ = compile_probe(ROOT / 'bin/boufbowl-client-1.9.6.swf', probe_changes)
    print('Preparing cached benchmark controls…', flush=True)
    client, reused = compile_probe(probe_base, changes)
    field = (ROOT / 'patches/FieldView.as').read_text()
    marker = 'this._cellsLayer.cacheAsBitmap = Capabilities.playerType == "PlugIn";'
    assert field.count(marker) == 1
    reference, _ = compile_probe(client, [
        ('com.ankamagames.boufbowl.client.match.strategic.view.field.FieldView',
         field.replace(marker, 'this._cellsLayer.cacheAsBitmap = false;'))])
    manifest = {'fixture_sha256': hashlib.sha256(data).hexdigest(),
                'client_sha256': hashlib.sha256(client.read_bytes()).hexdigest(),
                'ruffle': json.loads((ROOT / 'vendor/ruffle/package.json').read_text())['version'],
                'reference_client_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
                'actors': 10, 'stadium': 'Cania', 'turn_ticks': 800}
    (output / 'manifest.json').write_text(json.dumps(manifest))
    return client, output, reused, reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=9927)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be between1 and65535')
    client, output, reused, reference = build()
    print(json.dumps({'client': str(client), 'reused': reused}), flush=True)
    if args.build_only:
        return

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            route = unquote(urlsplit(self.path).path)
            files = {'/': ROOT / 'tools/browser-benchmark/index.html',
                     '/benchmark-client.swf': client,
                     '/benchmark-reference.swf': reference,
                     '/benchmark-runner.html': ROOT / 'tools/browser-benchmark/runner.html',
                     '/benchmark-fixture.json': output / 'fixture.json',
                     '/benchmark-manifest.json': output / 'manifest.json'}
            if route not in files:
                filename = (ROOT / route.lstrip('/')).resolve()
                allowed = [ROOT / 'assets', ROOT / 'resources', ROOT / 'vendor/ruffle', ROOT / 'tools/browser-benchmark']
                if not any(filename.is_relative_to(directory) for directory in allowed) or not filename.is_file():
                    self.send_error(404)
                    return
                return super().do_GET()
            file = files[route]
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(str(file)))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Length', str(file.stat().st_size))
            self.end_headers()
            self.wfile.write(file.read_bytes())

        def do_HEAD(self):
            self.send_error(405)

    with ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(ROOT))) as server:
        print(f'Benchmark: http://{args.host}:{args.port}/', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
