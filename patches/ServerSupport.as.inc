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
      private static var serverTournamentId:String;
      private static var serverAbilities:Object = {};
      public static var serverZobalMasks:Object = {};
      private static var serverLabel:TextField;
      private static var serverInMatch:Boolean = false;
      private static var serverCurrentMatch:String;
      private static var serverPanel:Sprite;
      private static var serverProfileName:String;
      private static var serverEmbedded:Boolean = false;
      private static var serverAuthMode:String = "device";
      private static var serverAccountUsername:String;
      private static var serverAccountBusy:Boolean = false;
      private static var serverQueueWaiting:Boolean = false;
      private static var serverSpectating:String;
      private static var serverSubscriptions:Array=[];
      public static function serverSubscribed(language:String) : Boolean { return serverSubscriptions.indexOf(language)>=0; }
      private static var serverReplayFile:flash.net.FileReference;

      public static function serverMode() : Boolean { return serverActive; }

      private static function serverStatus(text:String) : void
      {
         if(serverLabel == null)
         {
            serverLabel = new TextField();
            serverLabel.defaultTextFormat = new TextFormat("_sans",12,0xffffff);
            serverLabel.background = true;
            serverLabel.backgroundColor = 0x20252b;
            serverLabel.x = 10; serverLabel.y = 570; serverLabel.width = 512; serverLabel.height = 24;
            serverLabel.mouseEnabled = false;
         }
         serverLabel.width = Math.min(512, Stage(app.contextInjector.getInstance(Stage)).stageWidth / 2);
         serverLabel.wordWrap = true;
         serverLabel.text = text;
         serverLabel.height = Math.min(72, serverLabel.textHeight + 6);
         serverLabel.y = 594 - serverLabel.height;
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
         if(!resume)
         {
            var chat:com.ankamagames.boufbowl.client.chat.model.IChatModel = app.contextInjector.getInstance(com.ankamagames.boufbowl.client.chat.model.IChatModel);
            chat.clearMessages(); chat.clear();
         }
         serverGeneration++;
         serverAccountBusy = false;
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
         serverRequest("hello",{session:serverSession,nickname:profileName,clubs:clubs,language:AccountInformations(app.contextInjector.getInstance(AccountInformations)).lang},function(response:Object):void {
            if(!response.ok) { serverStatus("Connection failed: " + response.error); serverConnectionPanel(); return; }
            serverSession = String(response.session);
            serverStorage.data.session = serverSession;
            if(response.auth_mode == "device") serverStorage.data.deviceSession = serverSession;
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
         if(response.hasOwnProperty("spectating")) serverSpectating = response.spectating;
         if(response.subscriptions != null) serverSubscriptions=response.subscriptions;
         if(response.language != null) AccountInformations(app.contextInjector.getInstance(AccountInformations)).lang=String(response.language);
         if(response.abilities != null) serverAbilities = response.abilities;
         if(response.zobal_masks != null) serverZobalMasks = response.zobal_masks;
         if(response.hasOwnProperty("tournament_id")) serverTournamentId=response.tournament_id;
         if(response.club_names != null) serverNames = response.club_names;
         if(response.auth_mode != null) serverAuthMode = String(response.auth_mode);
         if(response.profile != null && response.profile.club_id != null) serverClubId=String(response.profile.club_id);
         if(response.profile != null) { serverAccountUsername = response.profile.account_username; if(response.profile.role != null) serverRole=String(response.profile.role); }
         if(response.matchmaking != null)
         {
            var waiting:Boolean = response.matchmaking.status == "waiting";
            if(waiting) serverStatus("Searching for an opponent (" + response.matchmaking.waiting_players + " players). Play opens search controls.");
            else if(serverQueueWaiting) serverStatus(response.current_match != null ? "Opponent found" : "Search ended");
            serverQueueWaiting = waiting;
         }
         if(response.profile != null) AccountInformations(app.contextInjector.getInstance(AccountInformations)).nickname = response.profile.nickname;
         if(response.current_match != null) serverCurrentMatch = String(response.current_match);
         else if(response.hasOwnProperty("current_match")) serverCurrentMatch = null;
      }

      public static function serverAbilityDescription(classId:int) : String
      {
         var names:Array = ["Cra","Ecaflip","Eniripsa","Enutrof","Feca","Iop","Osamodas","Pandawa","Rogue","Sacrier","Sadida","Sram","Xelor","Zobal"];
         var ability:Object = serverAbilities[names[classId-1]];
         if(ability == null) return "";
         var language:String = AccountInformations(app.contextInjector.getInstance(AccountInformations)).lang;
         if(ability.descriptions != null) return String(ability.descriptions[language] || ability.descriptions.en);
         return String(ITranslator(app.contextInjector.getInstance(ITranslator)).getEnumTranslation("classes_order_tooltip_desc_enum",classId));
      }

      private static function serverRequest(route:String, body:Object, complete:Function) : void
      {
         var generation:uint=serverGeneration;
         var loader:URLLoader=new URLLoader();
         var done:Boolean=false;
         var timeout:uint;
         var finish:Function=function(response:Object):void {
            if(done) return; done=true; clearTimeout(timeout);
            if(generation != serverGeneration) return;
            complete(response);
         };
         timeout=setTimeout(function():void {
            if(done) return;
            if(generation == serverGeneration) { app.hideMessageBox(); serverTrace("Request cancelled after 6 seconds: " + route); }
            try { finish({ok:false,retryable:false,code:"REQUEST_TIMEOUT",error:"Request cancelled after 6 seconds"}); }
            // URLLoader.close() terminates the legacy Windows player under Wine.
            // Retire this request and discard late completion instead.
            finally { loader.removeEventListener(Event.COMPLETE,onComplete); }
         },6000);
         var onComplete:Function=function(event:Event):void {
            try { finish(com.adobe.serialization.json.JSON.decode(String(loader.data))); }
            catch(error:Error) { serverStatus("Server response error: " + error.toString()); serverTrace("ERROR " + error.toString()); }
         };
         loader.addEventListener(Event.COMPLETE,onComplete);
         loader.addEventListener(IOErrorEvent.IO_ERROR,function(event:IOErrorEvent):void { finish({ok:false,retryable:true,error:event.text}); });
         loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR,function(event:SecurityErrorEvent):void { finish({ok:false,retryable:true,error:event.text}); });
         var request:URLRequest=new URLRequest(serverBase+route);
         request.method=URLRequestMethod.POST; request.contentType="application/json";
         request.data=com.adobe.serialization.json.JSON.encode(body);
         try { loader.load(request); } catch(error:Error) { finish({ok:false,retryable:true,error:error.message}); }
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
            else { if(body.request_class == "MatchRequestMessage") { MatchCreationModel(app.contextInjector.getInstance(MatchCreationModel)).matchRequestRunning=false;app.hideMessageBox(); } serverStatus("Request failed: " + response.error); serverTrace("ERROR " + response.error); }
            serverPump();
         });
      }

      private static function serverPoll() : void
      {
         if(!serverActive || serverSession == null || serverPolling) return;
         serverPolling = true;
         serverRequest("poll",{session:serverSession,cursor:serverCursor,wait_ms:1000},function(response:Object):void {
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
            else {
               serverStatus("Connection interrupted: " + response.error);
               if(response.code == "PLAYER_KICKED" || response.code == "PLAYER_BANNED" || response.code == "SESSION_INVALID") {
                  serverGeneration++;serverQueue=[];serverSending=false;stopMock();showHome();serverCurrentMatch=null;
                  serverStatus(response.error);return;
               }
            }
            serverPollTimer = setTimeout(serverPoll,response.ok ? 0 : 250);
         });
      }

      private static function serverPacket(packet:Object) : void
      {
         if(packet.round_states != null) serverTournamentRounds=packet.round_states;
         if(packet.channel == "COMMUNITY") { if(packet.type == "MODERATED") { serverStatus(packet.verb + ": " + packet.reason); if(packet.verb == "kick" || packet.verb == "ban") { stopMock();showHome(); } } if(packet.type == "SPECTATING_STOPPED") { serverSpectating=null; serverStatus("Stopped spectating"); showHome(); } return; }
         if(mockActive && packet.channel == "MATCH") return;
         if(packet.type == "RESOLUTION_SCENARIO") { app.hideMessageBox(); serverStatus("Loading turn animation"); }
         if(packet.type == "MATCH_INFORMATION") { serverClosePanel(); serverInMatch = true; }
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
         if(!chat && getQualifiedClassName(request).split("::").pop() == "WhoisRequestMessage")
         {
            serverPlayerInformation(String(request.nickname)); return;
         }
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
         var requestClass:String=getQualifiedClassName(request).split("::").pop();
         serverTrace("Outgoing " + requestClass);
         serverSend({operation:chat ? "chat" : "protocol",hex:hex,request_class:requestClass});
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

      public static function serverPlay() : void
      {
         if(serverCurrentMatch != null) { startServer(serverBase.replace(/\/api\/$/,""),null,true); return; }
         serverDialog("Play",310);
         var selectedClub:String=serverClubId;
         var clubIds:Array=[];
         for(var clubKey:String in serverNames) clubIds.push(clubKey);
         clubIds.sort(Array.NUMERIC);
         var clubLabel:TextField=serverText(serverPanel,"Team: " + serverNames[selectedClub],20,245,500);
         serverAction(serverPanel,"Change team",560,245,180,function():void {
            var clubIndex:int=clubIds.indexOf(selectedClub);
            selectedClub=String(clubIds[(clubIndex+1)%clubIds.length]);
            clubLabel.text="Team: " + serverNames[selectedClub];
         });
         var selected:int = 0;
         var stadiums:Array = @ENABLED_STADIUMS@;
         var names:Array = ["Any stadium","Farmstead","Brakmar","Beach","Bonta","Frigost","Kara","Forest","Ballotin","Pixel"];
         var stadiumLabel:TextField = serverText(serverPanel,"Any stadium",20,45,430);
         serverAction(serverPanel,"Change stadium",560,45,180,function():void {
            selected = (selected + 1) % (stadiums.length + 1);
            stadiumLabel.text = selected == 0 ? "Any stadium" : names[int(stadiums[selected-1])];
         });
         serverAction(serverPanel,"Find opponent",20,85,160,function():void {
            serverClosePanel(); serverSend({operation:"queue_join",club_id:selectedClub,stadiums:selected == 0 ? stadiums : [stadiums[selected-1]]});
         });
         serverAction(serverPanel,"CPU matchmaking",200,85,140,function():void {
            serverClosePanel(); serverSend({operation:"cpu_match",club_id:selectedClub,stadium:selected == 0 ? stadiums[0] : stadiums[selected-1]});
         });
         serverAction(serverPanel,"Cancel search",360,85,170,function():void { serverSend({operation:"queue_leave"}); });
         if(@TOURNAMENT_ENABLED@) serverAction(serverPanel,"Find tournament",20,200,220,function():void {
            serverClosePanel(); serverSend({operation:"tournament_match",club_id:selectedClub});
         });
         serverAction(serverPanel,"Community",550,200,180,function():void { serverCommunityPanel("Friends"); });
         serverText(serverPanel,"Challenge a player by nickname",20,130,500);
         var guest:TextField = serverInput(serverPanel,"",20,160,490);
         serverAction(serverPanel,"Challenge",540,160,180,function():void {
            serverClosePanel(); serverSend({operation:"challenge",club_id:selectedClub,nickname:guest.text,stadium:selected == 0 ? stadiums[0] : stadiums[selected-1]});
         });
      }

      private static function serverClosePanel() : void
      {
         if(serverPanel != null && serverPanel.parent != null) serverPanel.parent.removeChild(serverPanel);
      }

      private static function serverDialog(title:String, height:int) : void
      {
         serverClosePanel(); serverPanel = new Sprite();
         serverPanel.graphics.lineStyle(2,0xb3a66a); serverPanel.graphics.beginFill(0xf7f3d2); serverPanel.graphics.drawRoundRect(0,0,800,height,14); serverPanel.graphics.endFill();
         serverPanel.x = 110; serverPanel.y = Math.max(80,(600-height)/2);
         serverText(serverPanel,title,20,10,680);
         serverAction(serverPanel,"Close",690,10,90,function():void { serverClosePanel(); });
         Stage(app.contextInjector.getInstance(Stage)).addChild(serverPanel);
      }

      private static function serverText(parent:Sprite, text:String, x:int, y:int, width:int) : TextField
      {
         var field:TextField = new TextField(); field.defaultTextFormat = new TextFormat("_sans",15,0x463d2b);
         field.text = text; field.x = x; field.y = y; field.width = width; field.height = 28; parent.addChild(field); return field;
      }

      private static function serverInput(parent:Sprite, text:String, x:int, y:int, width:int, secret:Boolean = false) : TextField
      {
         var field:TextField = serverText(parent,text,x,y,width); field.type = "input";
         field.background = true; field.backgroundColor = 0xffffff; field.textColor = 0x000000;
         field.displayAsPassword = secret; parent.addChild(field); return field;
      }

      private static function serverAction(parent:Sprite, title:String, x:int, y:int, width:int, callback:Function) : Sprite
      {
         var button:Sprite = new Sprite(); button.x=x; button.y=y; button.buttonMode=true;
         button.graphics.lineStyle(1,0xb3a66a);button.graphics.beginFill(0xdce6a8); button.graphics.drawRoundRect(0,0,width,28,8); button.graphics.endFill();
         var label:TextField = serverText(button,title,4,2,width-8); label.mouseEnabled=false;
         button.addEventListener(MouseEvent.CLICK,function(event:MouseEvent):void { callback(); }); parent.addChild(button); return button;
      }

      private static function serverAccountPanel() : void
      {
         if(serverSession == null) { serverStatus("Connect to a server first"); return; }
         if(serverCurrentMatch != null) { serverStatus("Finish or surrender your match before changing accounts"); return; }
         serverDialog("Account: " + (serverAuthMode == "account" ? serverAccountUsername : "anonymous device"),330);
         serverText(serverPanel,"Username",20,55,130);
         var username:TextField = serverInput(serverPanel,serverAccountUsername != null ? serverAccountUsername : "",170,55,550);
         serverText(serverPanel,"Password",20,95,130);
         var password:TextField = serverInput(serverPanel,"",170,95,550,true);
         serverText(serverPanel,"New password",20,135,150);
         var replacement:TextField = serverInput(serverPanel,"",170,135,550,true);
         serverText(serverPanel,"Recovery code",20,175,150);
         var recovery:TextField = serverInput(serverPanel,"",170,175,550,true);
         serverAction(serverPanel,"Log in",20,215,130,function():void { serverAccountRequest("login",username,password,replacement); });
         serverAction(serverPanel,"Create / link",170,215,160,function():void { serverAccountRequest("register",username,password,replacement); });
         serverAction(serverPanel,"Change password",350,215,200,function():void { serverAccountRequest("password",username,password,replacement); });
         serverAction(serverPanel,"Log out",570,215,160,function():void { serverAccountRequest("logout",username,password,replacement); });
         serverAction(serverPanel,"Use device profile",20,255,220,function():void { serverUseDevice(); });
         serverAction(serverPanel,"Recover account",260,255,220,function():void { serverAccountRequest("recover",username,password,replacement,recovery); });
         serverText(serverPanel,"Passwords: 10–128 characters. Create links this profile and preserves your clubs.",20,295,740);
      }

      private static function serverUseDevice() : void
      {
         if(serverAccountBusy) return;
         serverStorage.data.session = serverStorage.data.deviceSession != null ? serverStorage.data.deviceSession : null;
         serverStorage.flush(); serverClosePanel();
         startServer(serverEmbedded ? "" : serverBase.replace(/\/api\/$/,""),serverProfileName);
      }

      private static function serverAccountRequest(action:String, username:TextField, password:TextField, replacement:TextField, recovery:TextField = null) : void
      {
         if(serverAccountBusy) return;
         if(action == "logout" && serverAuthMode == "device") { serverStatus("You are already using the device profile"); return; }
         serverAccountBusy = true;
         var clubs:Array = []; for(var i:int=0;i<teams.numItems;i++) clubs.push(serverSnapshot(teams.getItemAt(i)));
         serverRequest("account",{action:action,username:username.text,password:password.text,new_password:replacement.text,
             recovery_code:recovery != null ? recovery.text : null,session:serverSession,nickname:serverProfileName,clubs:clubs},function(response:Object):void {
            serverAccountBusy = false;
            if(!response.ok) { serverStatus(response.error); return; }
            password.text=""; replacement.text="";
               if(action == "logout") { delete serverStorage.data.accountSession; serverUseDevice(); return; }
            serverSession = String(response.session);
            serverStorage.data.session = serverSession; serverStorage.data.accountSession = serverSession;
            if(action == "password" || action == "recover") delete serverStorage.data.deviceSession;
            serverStorage.flush(); serverClosePanel();
            startServer(serverEmbedded ? "" : serverBase.replace(/\/api\/$/,""),serverProfileName);
            if(response.recovery_code != null)
            {
               serverDialog("Save your recovery code",180);
               serverText(serverPanel,"Keep this code privately. It can reset your password and is shown only now.",20,50,760);
               serverInput(serverPanel,String(response.recovery_code),20,95,720);
            }
         });
      }

      private static function serverConnectionPanel() : void
      {
         if(serverPanel != null && serverPanel.parent != null) serverPanel.parent.removeChild(serverPanel);
         serverPanel = new Sprite();
         serverPanel.graphics.lineStyle(2,0xb3a66a);serverPanel.graphics.beginFill(0xf7f3d2); serverPanel.graphics.drawRoundRect(0,0,800,300,14); serverPanel.graphics.endFill();
         serverPanel.x = 110; serverPanel.y = 150;
         var title:TextField = new TextField(); title.defaultTextFormat = new TextFormat("_sans",16,0x463d2b);
         title.text = "Connect to your Boufbowl server"; title.width = 760; title.height = 30; title.x = 20; title.y = 10;
         serverPanel.addChild(title);
         var input:TextField = new TextField(); input.type = "input"; input.background = true; input.backgroundColor = 0xffffff;
         input.defaultTextFormat = new TextFormat("_sans",16,0x000000); input.width = 620; input.height = 30; input.x = 20; input.y = 50;
         input.text = serverEmbedded ? "" : serverBase != null ? serverBase.replace(/\/api\/$/,"") : @DEFAULT_URL@;
         serverPanel.addChild(input);
         var profileLabel:TextField = new TextField(); profileLabel.text = "Device:"; profileLabel.textColor = 0x463d2b;
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
         serverAction(serverPanel,"Account",660,95,100,function():void { serverAccountPanel(); });
         serverAction(serverPanel,"Community",20,140,180,function():void { serverCommunityPanel("Friends"); });
         serverAction(serverPanel,"Wallet / cosmetics",220,140,220,function():void { serverWalletPanel(); });
         serverAction(serverPanel,"Leagues / seasons",460,140,250,function():void { serverProgressionPanel(); });
         serverAction(serverPanel,"News",20,185,180,function():void { serverNewsPanel(); });
         if(serverRole == "moderator" || serverRole == "admin") serverAction(serverPanel,"Moderation",220,185,220,function():void { serverModerationPanel(); });
         Stage(app.contextInjector.getInstance(Stage)).addChild(serverPanel);
      }

      private static function serverCommunityRequest(body:Object, complete:Function) : void
      {
         body.session = serverSession;
         body.request_id=String(getTimer()) + "-" + String(Math.random());
         serverRequest("community",body,function(response:Object):void {
            if(!response.ok) { serverStatus("Community: " + response.error); return; }
            serverMetadata(response); complete(response);
         });
      }

      private static function serverCommunityPanel(tab:String, offset:int = 0, selected:String = "", before:Number = 0) : void
      {
         if(serverSession == null) { serverStatus("Connect first"); return; }
         serverDialog("Community: " + tab,430); serverPanel.y=95;
         var panel:Sprite=serverPanel;
         var tabs:Array=["Friends","Rankings","History","Watch","Messages","Channels"];
         for(var i:int=0;i<tabs.length;i++) serverCommunityTab(String(tabs[i]),20+i*125);
         var listing:TextField=serverText(panel,"Loading...",20,85,760);
         listing.height=220; listing.multiline=true; listing.wordWrap=true; listing.selectable=true;
         var choice:TextField=serverInput(panel,selected,20,310,320);
         serverText(panel,tab == "History" || tab == "Watch" ? "Match ID" : "Player nickname",350,310,180);
         serverAction(panel,"Refresh",620,310,150,function():void { serverCommunityPanel(tab,offset,choice.text); });
         var friendMatches:Object={};
         var friendWatch:Sprite;
         var refreshWatch:Function=function():void { if(friendWatch != null) friendWatch.visible=friendMatches[choice.text.toLowerCase()] != null; };
         choice.addEventListener(Event.CHANGE,function(event:Event):void { refreshWatch(); });
         listing.addEventListener(MouseEvent.CLICK,function(event:MouseEvent):void {
            var character:int=listing.getCharIndexAtPoint(listing.mouseX,listing.mouseY);
            if(character<0) return;
            var line:String=listing.getLineText(listing.getLineIndexOfChar(character));
            var found:Array;
            if(tab == "Friends") { found=/^  (.*?) \((?:online|offline)/.exec(line); if(found != null) choice.text=found[1]; }
            else if(tab == "Rankings") { found=/^\d+\. (.*?)   /.exec(line); if(found != null) choice.text=found[1]; }
            else if(tab == "History" || tab == "Watch") { found=/^#(\d+)/.exec(line); if(found != null) choice.text=found[1]; }
            refreshWatch();
         });
         var action:String=tab == "Friends" || tab == "Channels" ? "overview" : tab == "Rankings" ? "rankings" : tab == "History" ? "history" : tab == "Watch" ? "live" : "messages";
         if(tab == "Messages")
         {
            listing.text="Enter a nickname and press Refresh to open a private conversation.";
            var messageCursor:Number=0;
            var messageRequest:Object={action:"messages",nickname:selected};
            if(before>0) messageRequest.before=before;
            if(selected != "") serverCommunityRequest(messageRequest,function(data:Object):void {
               if(serverPanel != panel) return;
               var lines:Array=[];
               for each(var message:Object in data.messages) lines.push(message["from"] + ": " + message.message);
               listing.text=lines.join("\n"); listing.scrollV=listing.maxScrollV; messageCursor=Number(data.before);
            });
            var draft:TextField=serverInput(panel,"",20,350,580);
            serverAction(panel,"Send",620,350,150,function():void {
               serverCommunityRequest({action:"message",nickname:choice.text,message:draft.text},function(data:Object):void { serverCommunityPanel("Messages",0,choice.text); });
            });
            serverAction(panel,"Older messages",20,390,180,function():void {
               if(messageCursor>0) serverCommunityPanel("Messages",0,choice.text,messageCursor);
            });
            return;
         }
         serverCommunityRequest({action:action,offset:offset},function(data:Object):void {
            if(serverPanel != panel) return;
            var lines:Array=[];
            if(tab == "Friends")
            {
               for each(var group:String in ["friends","incoming","outgoing","blocked"])
               {
                  lines.push(group.toUpperCase());
                  for each(var friend:Object in data[group])
                  {
                     lines.push("  " + friend.nickname + (friend.online ? " (online" + (friend.match != null ? ", match " + friend.match : "") + ")" : " (offline)"));
                     if(friend.match != null && group != "blocked") friendMatches[friend.nickname.toLowerCase()]=friend.match;
                  }
                  refreshWatch();
               }
            }
            else if(tab == "Channels")
            {
               choice.text=data.channels.join(",");
               lines.push("Subscribed global languages: " + data.channels.join(", "));
               lines.push("Each language is a separate room: fr, en, de, es.");
               lines.push("The match room includes both teams and spectators.");
               lines.push("Private conversations are saved and available in Messages.");
               lines.push("Blocked players cannot message, invite, spectate or queue against you.");
            }
            else if(tab == "Rankings")
               for each(var row:Object in data.rows) lines.push(row.rank + ". " + row.player.nickname + "   " + row.rating + " rating   W " + row.wins + " / D " + row.draws + " / L " + row.losses);
            else
               for each(var match:Object in data.matches) lines.push("#" + match.id + "  " + match.players.join(" vs ") + "  " + match.score.join(":") + (tab == "History" ? "  " + match.phase + " / " + match.turns + " turns" + (match.result_kind != null ? " / " + match.result_kind : "") + (match.side == null ? " (watched)" : "") : "  turn " + match.turn));
            listing.text=lines.length>0 ? lines.join("\n") : "No entries yet.";
            if(data.hasOwnProperty("more"))
            {
               if(offset>0) serverAction(panel,"Previous",500,390,130,function():void { serverCommunityPanel(tab,Math.max(0,offset-20),choice.text); });
               if(data.more) serverAction(panel,"Next",640,390,130,function():void { serverCommunityPanel(tab,offset+20,choice.text); });
            }
         });
         if(tab == "Friends")
         {
            var verbs:Array=["add","accept","reject","remove","block","unblock","cancel"];
            for(i=0;i<verbs.length;i++) serverFriendButton(String(verbs[i]),20+i*108,choice);
            serverAction(panel,"Message",20,390,130,function():void { serverCommunityPanel("Messages",0,choice.text); });
            serverAction(panel,"Challenge",165,390,145,function():void { serverClosePanel(); serverSend({operation:"challenge",nickname:choice.text,stadium:@ENABLED_STADIUMS@[0]}); });
            friendWatch=serverAction(panel,"Spectate",325,390,145,function():void { serverCommunityRequest({action:"spectate",nickname:choice.text},function(data:Object):void { serverClosePanel(); }); });
            refreshWatch();
         }
         else if(tab == "Rankings")
            serverAction(panel,"Find player",20,350,160,function():void {
               serverCommunityRequest({action:"rankings",nickname:choice.text},function(data:Object):void { serverCommunityPanel("Rankings",int(data.offset),choice.text); });
            });
         else if(tab == "History")
         {
            serverAction(panel,"Watch replay",20,350,180,function():void { serverLoadReplay(choice.text,false); });
            serverAction(panel,"Save replay",220,350,180,function():void { serverLoadReplay(choice.text,true); });
            serverAction(panel,"Open replay file",420,350,180,function():void {
               if(serverCurrentMatch != null || serverSpectating != null) { serverStatus("Leave the match before opening a replay"); return; }
               serverReplayFile=new flash.net.FileReference();
               serverReplayFile.addEventListener(Event.SELECT,function(event:Event):void { serverReplayFile.load(); });
               serverReplayFile.addEventListener(Event.COMPLETE,function(event:Event):void {
                  try { serverStartReplay(com.adobe.serialization.json.JSON.decode(serverReplayFile.data.toString())); }
                  catch(error:Error) { serverStatus("Invalid replay: " + error.message); }
               });
               serverReplayFile.browse([new flash.net.FileFilter("Boufbowl replay (*.json)","*.json")]);
            });
         }
         else if(tab == "Watch")
         {
            serverAction(panel,"Spectate",20,350,180,function():void { serverCommunityRequest({action:"spectate",match:choice.text},function(data:Object):void { serverClosePanel(); }); });
            serverAction(panel,"Stop spectating",220,350,200,function():void { serverCommunityRequest({action:"stop_spectating"},function(data:Object):void { serverSpectating=null; serverClosePanel(); showHome(); }); });
         }
         else if(tab == "Channels")
         {
            choice.text="en";
            serverText(panel,"Languages separated by commas",350,310,260);
            serverAction(panel,"Subscribe",20,350,180,function():void {
               var languages:Array=choice.text.replace(/\s/g,"").split(",");
               serverCommunityRequest({action:"channels",languages:languages,language:languages[0]},function(data:Object):void { AccountInformations(app.contextInjector.getInstance(AccountInformations)).lang=languages[0]; serverCommunityPanel("Channels"); });
            });
            serverAction(panel,"Report player",220,350,180,function():void { serverReportPanel(); });
         }
      }

      private static function serverCommunityTab(tab:String, x:int) : void
      {
         serverAction(serverPanel,tab,x,45,115,function():void { serverCommunityPanel(tab); });
      }

      private static function serverFriendButton(verb:String, x:int, choice:TextField) : void
      {
         serverAction(serverPanel,verb,x,350,100,function():void {
            serverCommunityRequest({action:"friend",verb:verb,nickname:choice.text},function(data:Object):void { serverCommunityPanel("Friends",0,choice.text); });
         });
      }

      private static function serverReportPanel() : void
      {
         serverDialog("Report a player to this server's operator",230);
         var nickname:TextField=serverInput(serverPanel,"",20,55,400);
         serverText(serverPanel,"Player nickname",440,55,300);
         var reason:TextField=serverInput(serverPanel,"",20,100,750);
         serverText(serverPanel,"Reason (stored locally for operator review)",20,140,750);
         serverAction(serverPanel,"Submit report",20,180,200,function():void {
            serverCommunityRequest({action:"report",nickname:nickname.text,reason:reason.text},function(data:Object):void { serverClosePanel(); serverStatus("Report saved for the server operator"); });
         });
      }

      private static function serverLoadReplay(matchId:String, save:Boolean) : void
      {
         if(!save && (serverCurrentMatch != null || serverSpectating != null)) { serverStatus("Leave your current match before watching a replay"); return; }
         serverRequest("replay",{session:serverSession,match:matchId},function(data:Object):void {
            if(!data.ok) { serverStatus("Replay: " + data.error); return; }
            if(save)
            {
               serverDialog("Replay ready to save",140);
               serverAction(serverPanel,"Save JSON file",20,65,240,function():void {
                  serverReplayFile=new flash.net.FileReference();
                  serverReplayFile.save(com.adobe.serialization.json.JSON.encode(data.replay),"boufbowl-match-" + matchId + ".json");
               });
            }
            else serverStartReplay(data.replay);
         });
      }

      private static function serverStartReplay(replay:Object) : void
      {
         if(replay.format_version != 1 || !(replay.steps is Array) || replay.steps.length == 0) throw new Error("Unsupported replay file");
         serverClosePanel(); stopMock(); serverInMatch=false;
         replayRoot=replay;serverZobalMasks=replay.chapters != null && replay.chapters.length>0 && replay.chapters[0].zobal_masks != null ? replay.chapters[0].zobal_masks : {};replayCurrentTurn=1;replaySpeed=1;replayPaused=false;
         mockFixture=replay; mockIndex=0; mockActive=true;replayBuildControls();
         mockStatus("Playing saved match; Home exits playback"); scheduleMockStep();
      }

      public static function serverSetBlock(nickname:String, enabled:Boolean) : void
      {
         serverCommunityRequest({action:"friend",verb:enabled ? "block" : "unblock",nickname:nickname},function(data:Object):void {
            serverStatus(nickname + (enabled ? " blocked" : " unblocked"));
         });
      }

      private static var serverClubId:String;
      private static var serverPlayers:Object={};
      public static function serverCanSpectate(nickname:String) : Boolean
      {
         var player:Object=serverPlayers[nickname.toLowerCase()];
         return player != null && player.can_spectate == true;
      }
      public static function serverPlayerLookup(nickname:String, ready:Function) : void
      {
         serverRequest("community",{session:serverSession,action:"player",nickname:nickname},function(data:Object):void {
            serverPlayers[nickname.toLowerCase()]=data.ok ? data : {can_spectate:false};
            ready();
         });
      }
      private static function serverLayoutToolbar() : void
      {
         toolbar.x=Math.max(0,Stage(app.contextInjector.getInstance(Stage)).stageWidth-toolbar.width-80);
      }

      public static function serverPlayerInformation(nickname:String) : void
      {
         serverCommunityRequest({action:"player",nickname:nickname},function(data:Object):void {
            serverTrace("Player information opened: " + data.nickname);
            serverDialog("Player: " + data.nickname,240);
            serverText(serverPanel,"Club: " + data.player.club.clubName,20,50,750);
            serverText(serverPanel,"Role: " + (data.role != null ? data.role : "player") + "   Rating: " + data.statistics.rating + "   Wins: " + data.statistics.wins + "   Draws: " + data.statistics.draws + "   Losses: " + data.statistics.defeats,20,90,750);
            serverText(serverPanel,data.online ? "Online" + (data.match != null ? " - match " + data.match : "") : "Offline",20,130,750);
            serverAction(serverPanel,"Private message",20,180,200,function():void { serverCommunityPanel("Messages",0,nickname); });
            if(data.can_spectate) serverAction(serverPanel,"Spectate match",250,180,200,function():void {
               serverCommunityRequest({action:"spectate",match:data.match},function(result:Object):void { serverClosePanel(); });
            });
         });
      }
