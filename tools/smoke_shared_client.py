"""Exercise shared client optimizations and a 3D fixture in native Adobe AIR."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from tools.build_tools import air_sdk, ffdec_jar, java_binary
from tools.game_config import ROOT, load_config, startup_source, flashvars_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', choices=('desktop', 'android', 'both'), default='both')
    parser.add_argument('--air-sdk', type=Path)
    parser.add_argument('--fixture', type=Path, default=ROOT/'resources/mock_match.json')
    parser.add_argument('--runtime-libs', type=Path, help='Optional directory for native AIR shared-library dependencies')
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    sdk = air_sdk(args.air_sdk)
    adl = sdk/'bin/adl'
    if not adl.is_file():
        raise RuntimeError('The AIR SDK does not contain a native ADL executable')
    evidence = ROOT/'.local/shared-client'
    evidence.mkdir(parents=True, exist_ok=True)
    modes = ('desktop', 'android') if args.root == 'both' else (args.root,)
    for mode in modes:
        with tempfile.TemporaryDirectory(prefix='native-'+mode+'-', dir=evidence) as work:
            work = Path(work)
            (work/'bin').mkdir()
            (work/'assets').symlink_to(ROOT/'assets', target_is_directory=True)
            shutil.copytree(ROOT/'resources', work/'resources')
            shutil.copyfile(args.fixture, work/'resources/mock_match.json')
            root = ROOT/('android/patches' if mode == 'android' else 'patches')/'BoufbowlClient.as'
            source = root.read_text()
            source = source.replace('\n{', '\n{\n   import flash.utils.getDefinitionByName;\n   import flash.utils.setTimeout;', 1)
            # The application id below isolates this test's preferences.
            source = source.replace('var frameRateTarget:Number = Number(preferences.data.frameRateTarget);',
                                    'preferences.data.frameRateTarget = 30;\n         var frameRateTarget:Number = Number(preferences.data.frameRateTarget);', 1)
            source = source.replace('stage.frameRate = frameRateTarget;',
                                    'stage.frameRate = frameRateTarget;\n         setTimeout(runSharedSmoke,4000);', 1)
            pos = source.rfind('   }')
            source = source[:pos] + (ROOT/'tools/shared_client_smoke.as.inc').read_text() + (ROOT/'tools/shared_client_bench.as.inc').read_text() + source[pos:]
            root_patch = work/'BoufbowlClient.as'
            root_patch.write_text(source)
            config = load_config()
            startup = startup_source((ROOT/'patches/StartUpApplicationCommand.as').read_text(), config, android=True)
            startup = startup.replace('private static function mockStatus(text:String, showToast:Boolean = false) : void\n      {',
                                      'private static function mockStatus(text:String, showToast:Boolean = false) : void\n      {\n'
                                      '         trace("SHARED_SMOKE REPLAY fps=" + Stage(app.contextInjector.getInstance(Stage)).frameRate + " " + text);\n'
                                      '         if(text.indexOf("ERROR:") == 0) setTimeout(function():void { Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit(1); },100);\n'
                                      '         if(text.indexOf("Fixture delivered") == 0) setTimeout(function():void { trace("SHARED_SMOKE REPLAY PASS"); Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit(0); },1000);', 1)
            startup_patch = work/'StartUpApplicationCommand.as'
            startup_patch.write_text(startup)
            flashvars = flashvars_source((ROOT/'patches/FlashVarsManager.as').read_text(), config)
            marker = '      public function getValue(param1:String) : String\n      {'
            flashvars = flashvars.replace(marker, marker+'\n         if(param1 == "mock" || param1 == "scene3d") return "1";\n         if(param1 == "server") return "0";', 1)
            flashvars_patch = work/'FlashVarsManager.as'
            flashvars_patch.write_text(flashvars)
            changes = ['com.ankamagames.boufbowl.BoufbowlClient', root_patch,
                       'com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand', startup_patch,
                       'com.ankamagames.xgaming.utils.flashvars.FlashVarsManager', flashvars_patch,
                       'com.ankamagames.jerakine.resources.adapters.impl.SwlAdapter', ROOT/'android/patches/SwlAdapter.as']
            compile_log = evidence/('native-'+mode+'-compile.log')
            with compile_log.open('w') as output:
                subprocess.run([str(java_binary()), '-jar', str(ffdec_jar()), '-replace',
                                str(ROOT/'bin/boufbowl-client-1.9.6.swf'), str(work/'bin/client.swf'),
                                *map(str, changes)], check=True, stdout=output, stderr=subprocess.STDOUT, timeout=600)
            descriptor = work/'application.xml'
            descriptor.write_text(f'''<application xmlns="http://ns.adobe.com/air/application/51.1">
<id>org.boufbowl.sharedsmoke.{mode}{time.time_ns()}</id><versionNumber>1.0.0</versionNumber><filename>Shared Client Smoke</filename>
<initialWindow><content>bin/client.swf</content><visible>true</visible><width>1024</width><height>600</height><renderMode>cpu</renderMode></initialWindow>
<supportedProfiles>desktop</supportedProfiles></application>''')
            env = dict(os.environ)
            if args.runtime_libs:
                env['LD_LIBRARY_PATH'] = str(args.runtime_libs.resolve()) + (':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
            command = [str(adl), '-profile', 'desktop', str(descriptor), str(work)]
            if not env.get('DISPLAY'):
                command = ['xvfb-run', '-a', *command]
            log = evidence/('native-'+mode+'.log')
            with log.open('w') as output:
                result = subprocess.run(command, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=args.timeout)
            text = log.read_text()
            if 'Linux runtime is limited to use by commercially licensed developers' in text:
                raise RuntimeError('Native AIR requires a commercial developer license on this host; no application code ran. See '+str(log))
            if result.returncode or 'SHARED_SMOKE PASS:' not in text or 'SHARED_SMOKE REPLAY PASS' not in text or 'SHARED_SMOKE FAIL:' in text:
                raise RuntimeError('Native '+mode+' smoke failed; see '+str(log))
            if 'fps=30 Playback mode 3D' not in text or 'Outgoing ResolutionDoneMessage' not in text:
                raise RuntimeError('Native '+mode+' did not complete 3D playback at the saved FPS limit; see '+str(log))
            print('Native '+mode+' root: shared optimization checks and 3D playback passed ('+str(log)+')', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
