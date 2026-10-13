      private static var serverActive:Boolean = false;
      private static var serverGeneration:uint = 0;
      private static var serverBase:String;
      private static var serverSession:String;
      private static var serverCursor:Number = 0;
      private static var serverStorage:SharedObject;
      private static var serverQueue:Array = [];
      private static var serverSending:Boolean = false;
      private static var serverPolling:Boolean = false;
      private static var serverPollTimer:uint;
      private static var serverNames:Object = {};
      private static var serverAbilities:Object = {};
      private static var serverLabel:TextField;
      private static var serverInMatch:Boolean = false;
      private static var serverCurrentMatch:String;
      private static var serverPanel:Sprite;
      private static var serverProfileName:String;
      private static var serverEmbedded:Boolean = false;

      public static function serverMode() : Boolean { return serverActive; }

      private static function serverStatus(text:String) : void
      {
         if(serverLabel == null)
         {
            serverLabel = new TextField();
            serverLabel.defaultTextFormat = new TextFormat("_sans",12,0xffffff);
            serverLabel.background = true;
            serverLabel.backgroundColor = 0x20252b;
            serverLabel.x = 10; serverLabel.y = 570; serverLabel.width = 1000; serverLabel.height = 24;
            serverLabel.mouseEnabled = false;
         }
         serverLabel.text = text;
         Stage(app.contextInjector.getInstance(Stage)).addChild(serverLabel);
      }

      private static function serverTrace(text:String) : void
      {
         if(@TRACE_URL@ != "")
         {
            var loader:URLLoader = new URLLoader();
            loader.addEventListener(IOErrorEvent.IO_ERROR,function(event:IOErrorEvent):void {});
            loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR,function(event:SecurityErrorEvent):void {});
            loader.load(new URLRequest(@TRACE_URL@ + "?event=" + encodeURIComponent("SERVER " + String(getTimer()) + " " + text)));
         }
      }

      private static function startServer(url:String = null, profileName:String = null, resume:Boolean = false) : void
      {
         var oldSession:String = serverSession;
         var oldStorage:SharedObject = serverStorage;
         var oldEmbedded:Boolean = serverEmbedded;
         var oldProfileName:String = serverProfileName;
         var explicitLocal:Boolean = url == "";
         stopMock();
         serverGeneration++;
         serverActive = true;
         clearTimeout(serverPollTimer);
         serverSending = false; serverPolling = false; serverQueue = [];
         serverInMatch = false;
         var vars:FlashVarsManager = app.contextInjector.getInstance(FlashVarsManager);
         var connection:SharedObject = SharedObject.getLocal("BoufbowlConnection","/");
         if(url == null) url = vars.getValue("backend");
         if(!explicitLocal && (url == null || url == "") && connection.data.url != null) url = String(connection.data.url);
         if(url == null || url == "") url = @DEFAULT_URL@;
         var embedded:Boolean = url == "";
         if(embedded) url = Stage(app.contextInjector.getInstance(Stage)).getChildAt(0).loaderInfo.url.split("/bin/")[0];
         if(resume) embedded = oldEmbedded;
         serverEmbedded = embedded;
         serverBase = url.replace(/\/+$/,"") + "/api/";
         if(profileName == null) profileName = vars.getValue("profile");
         if((profileName == null || profileName == "") && connection.data.profile != null) profileName = String(connection.data.profile);
         if(profileName == null || profileName == "") profileName = "Local Player";
         if(resume) profileName = oldProfileName;
         serverProfileName = profileName;
         serverStorage = SharedObject.getLocal("BoufbowlBackend_" + profileName.replace(/[^a-z0-9_-]/gi,"_") + "_" + (embedded ? "local" : serverBase.replace(/[^a-z0-9_-]/gi,"_")),"/");
         serverSession = serverStorage.data.session != null ? String(serverStorage.data.session) : null;
         if(resume) { serverStorage = oldStorage; serverSession = oldSession; }
         serverStatus("Connecting to " + url);
         var clubs:Array = [];
         for(var index:int=0;index<teams.numItems;index++) clubs.push(serverSnapshot(teams.getItemAt(index)));
         serverRequest("hello",{session:serverSession,nickname:profileName,clubs:clubs},function(response:Object):void {
            if(!response.ok) { serverStatus("Connection failed: " + response.error); serverConnectionPanel(); return; }
            serverSession = String(response.session);
            serverStorage.data.session = serverSession;
            serverCursor = Number(response.cursor);
            serverStorage.flush();
            connection.data.profile = profileName;
            if(!embedded) connection.data.url = url;
            else if(explicitLocal) delete connection.data.url;
            connection.flush();
            serverMetadata(response);
            serverStatus("Connected as " + response.profile.nickname);
            serverPump();
            serverPoll();
         });
      }

      private static function serverMetadata(response:Object) : void
      {
         if(response.abilities != null) serverAbilities = response.abilities;
         if(response.club_names != null) serverNames = response.club_names;
         if(response.profile != null) AccountInformations(app.contextInjector.getInstance(AccountInformations)).nickname = response.profile.nickname;
         if(response.current_match != null) serverCurrentMatch = String(response.current_match);
         else if(response.hasOwnProperty("current_match")) serverCurrentMatch = null;
      }

      public static function serverAbilityDescription(classId:int) : String
      {
         var names:Array = ["Cra","Ecaflip","Eniripsa","Enutrof","Feca","Iop","Osamodas","Pandawa","Rogue","Sacrier","Sadida","Sram","Xelor","Zobal"];
         var ability:Object = serverAbilities[names[classId-1]];
         if(ability == null) return "";
         var text:String = "All active teammates: heal up to " + ability.heal + " HP";
         if(ability.element != null && ability.bonus != 0) text += ", +" + ability.bonus + " " + ability.element + " for this turn";
         return text + ".";
      }

      private static function serverRequest(route:String, body:Object, complete:Function) : void
      {
         var generation:uint = serverGeneration;
         var loader:URLLoader = new URLLoader();
         loader.addEventListener(Event.COMPLETE,function(event:Event):void {
            if(generation != serverGeneration) return;
            try { complete(com.adobe.serialization.json.JSON.decode(String(loader.data))); }
            catch(error:Error) { serverStatus("Server response error: " + error.toString()); serverTrace("ERROR " + error.toString()); }
         });
         loader.addEventListener(IOErrorEvent.IO_ERROR,function(event:IOErrorEvent):void {
            if(generation == serverGeneration) complete({ok:false,retryable:true,error:event.text});
         });
         loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR,function(event:SecurityErrorEvent):void {
            if(generation == serverGeneration) complete({ok:false,retryable:true,error:event.text});
         });
         var request:URLRequest = new URLRequest(serverBase + route);
         request.method = URLRequestMethod.POST;
         request.contentType = "application/json";
         request.data = com.adobe.serialization.json.JSON.encode(body);
         loader.load(request);
      }

      private static function serverSend(body:Object) : void
      {
         body.request_id = String(getTimer()) + "-" + String(Math.random()) + "-" + String(serverQueue.length);
         serverQueue.push(body);
         serverPump();
      }

      private static function serverPump() : void
      {
         if(!serverActive || serverSession == null || serverSending || serverQueue.length == 0) return;
         serverSending = true;
         var body:Object = serverQueue[0];
         body.session = serverSession;
         serverRequest("command",body,function(response:Object):void {
            serverSending = false;
            if(response.retryable) { serverStatus("Connection interrupted; retrying command"); setTimeout(serverPump,1500); return; }
            serverQueue.shift();
            if(response.ok) serverMetadata(response);
            else { serverStatus("Request failed: " + response.error); serverTrace("ERROR " + response.error); }
            serverPump();
         });
      }

      private static function serverPoll() : void
      {
         if(!serverActive || serverSession == null || serverPolling) return;
         serverPolling = true;
         serverRequest("poll",{session:serverSession,cursor:serverCursor},function(response:Object):void {
            serverPolling = false;
            if(response.ok)
            {
               serverMetadata(response);
               for each(var packet:Object in response.events)
               {
                  serverPacket(packet);
                  serverCursor = Number(packet.seq);
               }
            }
            else serverStatus("Connection interrupted: " + response.error);
            serverPollTimer = setTimeout(serverPoll,500);
         });
      }

      private static function serverPacket(packet:Object) : void
      {
         if(packet.type == "MATCH_INFORMATION") serverInMatch = true;
         if(packet.channel == "MATCH" && !serverInMatch) return;
         var data:ByteArray = new ByteArray();
         var hex:String = String(packet.hex);
         if(hex.length % 2 != 0 || hex.length > 262144 || /[^0-9a-f]/i.test(hex)) throw new Error("Invalid server envelope");
         for(var index:int=0;index<hex.length;index+=2) data.writeByte(parseInt(hex.substr(index,2),16));
         data.position = 0;
         var message:Object = packet.channel == "CHAT" ? new com.ankamagames.xgaming.chat.protocol.ChatMessage() : new BoufbowlMessage();
         message.readExternal(data);
         var pipeline:ChannelPipeline = app.contextInjector.getInstance(ChannelPipeline,packet.channel);
         if(packet.channel == "CHAT") pipeline.sendDataUpstream(message,app.contextInjector.getInstance(com.ankamagames.boufbowl.client.chat.network.ChatMessageHandler));
         else if(packet.channel == "MATCH") pipeline.sendDataUpstream(message,app.contextInjector.getInstance(MatchMessageHandler));
         else pipeline.sendDataUpstream(message,app.contextInjector.getInstance(LobbyMessageHandler));
         serverTrace("Incoming " + packet.type);
         if(packet.type == "MATCH_END") serverCurrentMatch = null;
      }

      private static function serverOutgoing(request:Object) : void
      {
         var chat:Boolean = getQualifiedClassName(request).indexOf("com.ankamagames.xgaming.chat.protocol::") == 0;
         var message:Object = chat ? new com.ankamagames.xgaming.chat.protocol.UnionProtocol().encode(request) : new com.ankamagames.boufbowl.protocol.UnionProtocol().encode(request);
         var data:ByteArray = new ByteArray();
         message.writeExternal(data);
         var hex:String = "";
         data.position = 0;
         while(data.bytesAvailable > 0)
         {
            var value:String = data.readUnsignedByte().toString(16);
            hex += value.length == 1 ? "0" + value : value;
         }
         serverTrace("Outgoing " + getQualifiedClassName(request).split("::").pop());
         serverSend({operation:chat ? "chat" : "protocol",hex:hex});
      }

      private static function serverColor(color:Color3) : Object { return {r:color.r,g:color.g,b:color.b}; }

      // The original Int64.toString concatenates high/low words, and UInt64
      // inherits Object.toString. Divide the two words without Number precision loss.
      private static function serverId(value:Object) : String
      {
         var high:Number = uint(value.high);
         var low:Number = uint(value.low);
         var negative:Boolean = value is Int64 && int(value.high) < 0;
         if(negative)
         {
            low = uint(~uint(low)) + 1;
            var carry:Number = low >= 4294967296 ? 1 : 0;
            low %= 4294967296;
            high = uint(~uint(high)) + carry;
         }
         var text:String = "";
         do
         {
            var nextHigh:Number = Math.floor(high / 10);
            var combined:Number = (high - nextHigh * 10) * 4294967296 + low;
            var nextLow:Number = Math.floor(combined / 10);
            text = String(combined - nextLow * 10) + text;
            high = nextHigh; low = nextLow;
         } while(high != 0 || low != 0);
         return (negative ? "-" : "") + text;
      }

      private static function serverSnapshot(club:ClubModel) : Object
      {
         var info:ClubInformation = club.clubInformation;
         var players:Array = [];
         for each(var player:IClubBoufbowlerModel in club.boufbowlers.toArray())
         {
            var data:Object = {id:serverId(player.id),name:player.name,boufbowlerClass:player.boufbowlerClass,
               gender:player.gender,paletteId:player.paletteId,hairColor:serverColor(player.hairColor),
               eyeColor:serverColor(player.eyeColor),skinColor:serverColor(player.skinColor),
               attributes:{earth:player.attributes.earth,air:player.attributes.air,fire:player.attributes.fire,water:player.attributes.water,
                  maxHitPoints:player.attributes.maxHealth,hitPointRegenRate:player.attributes.regeneration}};
            if(player.isUniqueCharacter) data.uniqueCharacter = player.uniqueCharacter;
            players.push(data);
         }
         return {clubId:serverId(info.id),clubName:info.name,boufbowler:players,paletteId:info.paletteId,
            firstColor:serverColor(info.mainColor),secondColor:serverColor(info.alternateColor),patternColor:serverColor(info.sigilColor),
            sigilBackground:info.sigilBackground,sigilCharge:info.sigilCharge,isPredefinedClub:false};
      }

      public static function persistClub(club:ClubModel) : void
      {
         if(serverActive) { serverStatus("Saving club..."); serverSend({operation:"save_club",club:serverSnapshot(club)}); }
      }

      private static function serverPlay() : void
      {
         if(serverCurrentMatch != null) { startServer(serverBase.replace(/\/api\/$/,""),null,true); return; }
         var creation:MatchCreationModel = app.contextInjector.getInstance(MatchCreationModel);
         serverSend({operation:"cpu_match",stadium:creation.hasSelectedStadium ? creation.selectedStadium : 1});
      }

      private static function serverConnectionPanel() : void
      {
         if(serverPanel != null && serverPanel.parent != null) serverPanel.parent.removeChild(serverPanel);
         serverPanel = new Sprite();
         serverPanel.graphics.beginFill(0x20252b); serverPanel.graphics.drawRect(0,0,800,155); serverPanel.graphics.endFill();
         serverPanel.x = 110; serverPanel.y = 180;
         var title:TextField = new TextField(); title.defaultTextFormat = new TextFormat("_sans",16,0xffffff);
         title.text = "Connect to your Boufbowl server"; title.width = 760; title.height = 30; title.x = 20; title.y = 10;
         serverPanel.addChild(title);
         var input:TextField = new TextField(); input.type = "input"; input.background = true; input.backgroundColor = 0xffffff;
         input.defaultTextFormat = new TextFormat("_sans",16,0x000000); input.width = 620; input.height = 30; input.x = 20; input.y = 50;
         input.text = serverEmbedded ? "" : serverBase != null ? serverBase.replace(/\/api\/$/,"") : @DEFAULT_URL@;
         serverPanel.addChild(input);
         var profileLabel:TextField = new TextField(); profileLabel.text = "Profile:"; profileLabel.textColor = 0xffffff;
         profileLabel.x = 20; profileLabel.y = 100; profileLabel.width = 80; profileLabel.height = 25;
         serverPanel.addChild(profileLabel);
         var profile:TextField = new TextField(); profile.type = "input"; profile.background = true; profile.backgroundColor = 0xffffff;
         profile.defaultTextFormat = new TextFormat("_sans",16,0x000000); profile.width = 520; profile.height = 28; profile.x = 120; profile.y = 95;
         profile.text = serverProfileName != null ? serverProfileName : "Local Player";
         serverPanel.addChild(profile);
         var button:Sprite = new Sprite(); button.graphics.beginFill(0x3578cf); button.graphics.drawRect(0,0,100,30); button.graphics.endFill();
         button.x = 660; button.y = 50;
         var label:TextField = new TextField(); label.text = "Connect"; label.textColor = 0xffffff; label.width = 100; label.height = 30; label.mouseEnabled = false;
         button.addChild(label); button.buttonMode = true;
         button.addEventListener(MouseEvent.CLICK,function(event:MouseEvent):void {
            serverPanel.parent.removeChild(serverPanel); startServer(input.text,profile.text);
         });
         serverPanel.addChild(button);
         Stage(app.contextInjector.getInstance(Stage)).addChild(serverPanel);
      }
