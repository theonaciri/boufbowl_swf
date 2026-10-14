"""Include live transport without changing the original archive or offline mode."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def inject_server(source, config, android=False):
    imports = "   import flash.net.SharedObject;\n   import flash.net.URLRequestMethod;\n"
    source = source.replace("   public class StartUpApplicationCommand", imports + "\n   public class StartUpApplicationCommand", 1)
    helper = (ROOT / "patches/ServerSupport.as.inc").read_text()
    helper = helper.replace("@ENABLED_STADIUMS@", json.dumps([i for i,name in enumerate(("FARMSTEAD","BRAKMAR","BEACH","BONTA","FRIGOST","KARA","FOREST","BALLOTIN","PIXEL"),1) if config["stadiums"][name]["enabled"]]))
    tournament=config["general"].get("tournament",{"enabled":False})
    helper=helper.replace("@TOURNAMENT_ENABLED@",str(tournament["enabled"]).lower()).replace("@TOURNAMENT_ID@",json.dumps(tournament.get("id",1)))
    host = config["general"]["server"]["host"]
    port = config["general"]["server"]["port"]
    helper = helper.replace("@DEFAULT_URL@", json.dumps(f"http://{host}:{port}" if android else ""))
    helper = helper.replace("@TRACE_URL@", json.dumps("" if android else "../__mock_trace"))
    source = source.replace("      private static function displayer()", helper + "\n      private static function displayer()", 1)
    source = re.sub(r"(public static function offlineRequest\(request:Object\) : void\s*\{)",
                    r"\1\n         if(serverActive && !mockActive) { serverOutgoing(request); return; }", source, count=1)
    source = re.sub(r"(public static function showHome\(\) : void\s*\{)", r"\1\n         serverInMatch = false;", source, count=1)
    source = re.sub(r"(public static function showTeams\(\) : void\s*\{)",
                    r'\1\n         if(serverActive) { serverSend({operation:"clubs"}); return; }', source, count=1)
    source = re.sub(r"(public static function teamName\(id:UInt64\) : String\s*\{)",
                    r"\1\n         if(serverActive && id != null && serverNames[serverId(id)] != null) return serverNames[serverId(id)];", source, count=1)
    enabled = str(config["general"]["startup_mode"] == "server").lower()
    hook = 'if(vars.getValue("server") == "1" || (vars.getValue("server") == null && ' + enabled + ')) setTimeout(startServer,100);'
    source = source.replace("createToolbar();", "createToolbar();\n         " + hook, 1)
    source = source.replace('addButton("Offline",8,60,null);', 'addButton("Play",8,60,function():void { if(serverActive) serverPlay(); });')
    source = source.replace('toolbar.graphics.drawRect(0,0,348,26);', 'toolbar.graphics.drawRect(0,0,404,26);')
    source = source.replace('Stage(app.contextInjector.getInstance(Stage)).addChild(toolbar);',
                            'addButton("Server",343,55,function():void { serverConnectionPanel(); });\n         Stage(app.contextInjector.getInstance(Stage)).addChild(toolbar);\n         serverLayoutToolbar();\n         Stage(app.contextInjector.getInstance(Stage)).addEventListener(Event.RESIZE,function(event:Event):void { serverLayoutToolbar(); });')
    source = source.replace('if(mockActive) mockStatus(text);', 'if(mockActive) mockStatus(text); else if(serverActive) serverTrace(text);')
    return source
