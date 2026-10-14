"""Include live transport without changing the original archive or offline mode."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def inject_server(source, config, android=False):
    imports = "   import flash.net.SharedObject;\n   import flash.net.URLRequestMethod;\n"
    source = source.replace("   public class StartUpApplicationCommand", imports + "\n   public class StartUpApplicationCommand", 1)
    helper = (ROOT / "patches/ServerSupport.as.inc").read_text() + "\n" + (ROOT / "patches/FrontendFeatures.as.inc").read_text()
    helper=helper.replace("@LOCAL_UI@",json.dumps(json.loads((ROOT/'resources/local_ui.json').read_text()),ensure_ascii=True))
    palettes=json.loads((ROOT/'resources/palettes.json').read_text())
    previews={}
    for kind,key in (('club_palette','club_palettes'),('character_palette','character_palettes')):
        for palette in palettes[key]:
            colors=palette.get('colors') or palette['hair'][:2]+palette['eyes'][:1]+palette['skin'][:2]
            previews[kind+':'+str(palette['id'])]=colors
    helper=helper.replace("@COSMETIC_PALETTES@",json.dumps(previews))
    helper = helper.replace("@ENABLED_STADIUMS@", json.dumps([i for i,name in enumerate(("FARMSTEAD","BRAKMAR","BEACH","BONTA","FRIGOST","KARA","FOREST","BALLOTIN","PIXEL"),1) if config["stadiums"][name]["enabled"]]))
    tournament=config["general"].get("tournament",{"enabled":False})
    helper=helper.replace("@TOURNAMENT_ENABLED@",str(tournament["enabled"]).lower())
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
    start=source.index('      private static function createToolbar()')
    end=source.index('      private static function addButton(',start)
    quit_action='Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit();' if android else 'fscommand("quit");'
    source=source[:start]+"""      private static function createToolbar() : void
      {
         toolbar=new Sprite();toolbar.graphics.beginFill(0xfffce8,.95);
         toolbar.graphics.drawRect(0,0,182,28);toolbar.graphics.endFill();
         addButton("Home",4,55,function():void { serverClosePanel();showHome(); });
         addButton("Quit",66,50,function():void { """+quit_action+""" });
         addButton("Server",123,55,function():void { serverConnectionPanel(); });
         Stage(app.contextInjector.getInstance(Stage)).addChild(toolbar);
         serverLayoutToolbar();
         Stage(app.contextInjector.getInstance(Stage)).addEventListener(Event.RESIZE,function(event:Event):void { serverLayoutToolbar(); });
      }

"""+source[end:]
    start=source.index('      private static function addButton(')
    match=re.search(r'\n      (?:public|private|override)',source[start+10:])
    if match:
        end=start+10+match.start()
    else:
        end=source.rfind('   }')
    source=source[:start]+"""      private static function addButton(label:String, xPos:int, width:int, callback:Function) : void
      {
         serverAction(toolbar,label,xPos,0,width,callback != null ? callback : function():void {});
      }
"""+source[end:]
    source=source.replace('toolbar.graphics.beginFill(0x20252b,0.95);','toolbar.graphics.beginFill(0xfffce8,.95);').replace('toolbar.graphics.beginFill(2106667,0.95);','toolbar.graphics.beginFill(0xfffce8,.95);')
    source = source.replace('if(mockActive) mockStatus(text);', 'if(mockActive) mockStatus(text); else if(serverActive) serverTrace(text);')
    return source
