"""Build a temporary real-view regression probe for the 2D possession timeline."""
import argparse
import json
from tools.client_probe import ROOT_CLASS,compile_probe,probe_root,replace_once,serve_probe
from tools.game_config import ROOT

VIEW_CLASS='com.ankamagames.boufbowl.client.match.strategic.view.field.boufbowler.BoufbowlerFieldRepresentationView'


def build_probe():
    view=(ROOT/'patches/BoufbowlerFieldRepresentationView.as').read_text()
    view=view.replace('getTimer()','possessionProbeClock()')
    view=replace_once(view,'var elapsed:int =','this.possessionProbeLastTime = possessionProbeClock();\n         var elapsed:int =')
    methods='''
      public static var possessionProbeTime:int = -1;
      public var possessionProbeLastTime:int = 0;
      private static function possessionProbeClock():int { return possessionProbeTime < 0 ? getTimer() : possessionProbeTime; }
      public function possessionProbeTick():void { this.updatePossessionAnimation(null); }
      public function possessionProbeInfo():Object {
         return {frame:currentFrame,totalFrames:totalFrames,hasBall:this._hasBall,running:this._possessionRunning,
            sampledAt:possessionProbeClock(),updatedAt:this.possessionProbeLastTime,
            elapsed:this._possessionElapsed,started:this._possessionStartedAt,front:boufballFront.visible,back:boufballBack.visible,
            frontFrames:boufballFront.totalFrames,backFrames:boufballBack.totalFrames};
      }
'''
    position=view.rfind('   }');view=view[:position]+methods+view[position:]
    source=probe_root('desktop')
    marker='this.initializeClientRuntime(true);'
    source=replace_once(source,marker,marker+'''
         if(flash.external.ExternalInterface.available) {
            flash.external.ExternalInterface.addCallback("probePossession",possessionSmoke);
            flash.external.ExternalInterface.addCallback("probePossessionLive",possessionLive);
         }
''')
    position=source.rfind('   }')
    source=source[:position]+(ROOT/'tools/possession_client_smoke.as.inc').read_text()+source[position:]
    return compile_probe(ROOT/'bin/boufbowl-client-1.9.6.swf',[(ROOT_CLASS,source),(VIEW_CLASS,view)])


def fixture():
    from tools.build_mock_fixture import build_fixture
    data=build_fixture()
    data['steps']=data['steps'][:2]
    data['name']='2D possession animation probe: static tactical field'
    path=ROOT/'.local/client-probes/possession-fixture.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n')
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve',action='store_true');parser.add_argument('--port',type=int,default=9919)
    args=parser.parse_args()
    client,reused=build_probe();print(json.dumps({'status':'compiled','client':str(client),'reused':reused}),flush=True)
    if args.serve:serve_probe(client,fixture(),args.port)


if __name__=='__main__':main()
