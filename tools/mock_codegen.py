"""Include the shared AS3 fixture harness in desktop and AIR startup patches."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def inject_mock(source, config, android=False):
    imports = """   import flash.events.Event;
   import flash.events.IOErrorEvent;
   import flash.events.SecurityErrorEvent;
   import flash.net.URLLoader;
   import flash.net.URLRequest;
   import flash.utils.ByteArray;
   import flash.utils.clearTimeout;
   import flash.utils.getTimer;
   import com.ankamagames.boufbowl.protocol.BoufbowlMessage;
   import com.ankamagames.boufbowl.client.match.MatchMessageHandler;
   import com.ankamagames.xgaming.net.channel.pipeline.ChannelPipeline;
"""
    source = source.replace("   public class StartUpApplicationCommand", imports + "\n   public class StartUpApplicationCommand", 1)
    helper = (ROOT / "patches/MockReplaySupport.as.inc").read_text()
    fixture_url = "app:/resources/mock_match.json" if android else "../resources/mock_match.json"
    helper = helper.replace("@FIXTURE_URL@", json.dumps(fixture_url))
    helper = helper.replace("@TRACE_URL@", json.dumps("" if android else "../__mock_trace"))
    source = source.replace("      private static function displayer()", helper + "\n      private static function displayer()", 1)
    source, count = re.subn(r"(public static function offlineRequest\(request:Object\) : void\s*\{)",
                           r"\1\n         if(mockActive) { mockOutgoing(request); return; }", source, count=1)
    if count != 1:
        raise ValueError("Cannot locate offline request interception seam")
    source = re.sub(r"(public static function showHome\(\) : void\s*\{)",
                    r"\1\n         stopMock();", source, count=1)
    enabled = str(config["general"]["startup_mode"] == "mock").lower()
    hook = 'if(vars.getValue("mock") == "1" || (vars.getValue("mock") == null && ' + enabled + ')) setTimeout(startMock,100);'
    if source.count("createToolbar();") != 1:
        raise ValueError("Cannot locate mock startup hook")
    return source.replace("createToolbar();", "createToolbar();\n         " + hook, 1)
