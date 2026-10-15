      private static var serverClientId:String;
      private static var serverTelemetryEnabled:Boolean = false;
      private static var serverTelemetryQueue:Array = [];
      private static var serverTelemetrySending:Boolean = false;
      private static var serverTelemetryTimer:uint;
      private static var serverTelemetryFailures:uint = 0;
      private static var serverConnectionLostAt:int = -1;
      private static var serverLastLatencyReport:int = -30000;

      private static function serverClientInfo() : Object
      {
         var vars:FlashVarsManager = app.contextInjector.getInstance(FlashVarsManager);
         var platform:String = vars.getValue("clientPlatform");
         var runtime:String = vars.getValue("clientRuntime");
         if(platform == null || platform == "") platform = @CLIENT_PLATFORM@;
         var reported:String = flash.system.Capabilities.os;
         if(platform == "unknown") {
            if(flash.system.Capabilities.playerType == "PlugIn") platform="browser";
            else if(/android/i.test(reported))platform="android";
            else if(/linux/i.test(reported))platform="linux";
            else if(/mac/i.test(reported))platform="macos";
            else if(/windows/i.test(reported))platform="windows";
         }
         if(runtime == null || runtime == "")runtime = @CLIENT_RUNTIME@;
         var stage:Stage = Stage(app.contextInjector.getInstance(Stage));
         return {platform:platform,runtime:runtime,game_version:"1.9.6",runtime_version:flash.system.Capabilities.version,
                 host_os:vars.getValue("clientOS"),reported_os:reported,cpu:flash.system.Capabilities.cpuArchitecture,
                 browser:vars.getValue("clientBrowser"),language:AccountInformations(app.contextInjector.getInstance(AccountInformations)).lang,
                 client_build:vars.getValue("v"),screen_width:int(flash.system.Capabilities.screenResolutionX),
                 screen_height:int(flash.system.Capabilities.screenResolutionY),gpu:stage.wmodeGPU,debugger:flash.system.Capabilities.isDebugger};
      }

      private static function serverInitTracking() : void
      {
         var storage:SharedObject=SharedObject.getLocal("BoufbowlClient","/");
         if(storage.data.clientId == null) {
            storage.data.clientId=String(new Date().time)+"-"+String(Math.random()).replace(".","");
            storage.flush();
         }
         serverClientId=String(storage.data.clientId);
         serverTelemetryEnabled=false;serverTelemetryQueue=[];serverTelemetrySending=false;
         serverTelemetryFailures=0;serverConnectionLostAt=-1;serverLastLatencyReport=-30000;clearTimeout(serverTelemetryTimer);
         try {
            var stage:Stage=Stage(app.contextInjector.getInstance(Stage));
            stage.getChildAt(0).loaderInfo.uncaughtErrorEvents.addEventListener("uncaughtError",serverUncaughtError,false,0,true);
         } catch(error:Error) {}
      }

      private static function serverUncaughtError(event:Event) : void
      {
         try {
            var error:Object=Object(event).error;
            serverRecordTelemetry({kind:"error",code:"UNCAUGHT_ERROR",message:error is Error ? Error(error).message : String(error),
                                   stack:error is Error ? Error(error).getStackTrace() : ""});
         } catch(ignored:Error) {}
      }

      private static function serverRecordTelemetry(event:Object) : void
      {
         if(!serverTelemetryEnabled || !serverActive || serverSession == null)return;
         event.id=String(getTimer())+"-"+String(Math.random()).replace(".","");
         if(serverTelemetryQueue.length >= 32)serverTelemetryQueue.shift();
         serverTelemetryQueue.push(event);
         if(!serverTelemetrySending && serverTelemetryTimer == 0)serverTelemetryTimer=setTimeout(serverFlushTelemetry,1000);
      }

      private static function serverFlushTelemetry() : void
      {
         serverTelemetryTimer=0;
         if(!serverTelemetryEnabled || !serverActive || serverSession == null || serverTelemetrySending || serverTelemetryQueue.length == 0)return;
         serverTelemetrySending=true;
         var batch:Array=serverTelemetryQueue.slice(0,20);
         serverRequest("telemetry",{session:serverSession,events:batch},function(response:Object):void {
            serverTelemetrySending=false;
            if(response.ok) {
               for(var index:int=0;index<batch.length;index++) {
                  if(serverTelemetryQueue.length>0 && serverTelemetryQueue[0].id == batch[index].id)serverTelemetryQueue.shift();
               }
               serverTelemetryFailures=0;
               if(serverTelemetryQueue.length>0)serverTelemetryTimer=setTimeout(serverFlushTelemetry,1000);
            } else if(response.retryable) {
               serverTelemetryFailures++;
               serverTelemetryTimer=setTimeout(serverFlushTelemetry,Math.max(1000,serverRetryDelay(serverTelemetryFailures)));
            } else {
               serverTelemetryQueue=[];
            }
         });
      }

      private static function serverStatsPanel() : void
      {
         serverDialog("Server statistics",380);
         var panel:Sprite=serverPanel;
         var listing:TextField=serverText(panel,"Loading…",20,60,760);listing.height=235;listing.multiline=true;listing.wordWrap=true;
         serverRequest("metrics",{session:serverSession,days:30},function(data:Object):void {
            if(serverPanel != panel)return;
            if(!data.ok) { listing.text=String(data.error);return; }
            listing.text="Online: "+data.online+"   Peak online: "+(data.peak_online == null ? "—" : data.peak_online)+
               "\nProfiles: "+data.totals.profiles+"   Accounts: "+data.totals.accounts+
               "\n30-day active users: "+data.usage.active_users+"   Returning users: "+data.usage.returning_users+
               "\nActive matches: "+data.active_matches+"   Queue: "+data.queued+
               "\n30-day matches: "+data.matches.started+" started / "+data.matches.completed+" completed"+
               "\nCPU: "+data.matches.cpu+"   Human: "+data.matches.human+"   Surrendered: "+data.matches.surrendered+
               "\nChat messages (total): "+data.totals.chat_messages+"   Turns saved: "+data.totals.turns+
               "\nHistorical activity before collection is partial. Full daily tables and diagnostics are in the dashboard.";
         });
         serverAction(panel,"Refresh",20,310,180,function():void { serverStatsPanel(); });
         serverAction(panel,"Open dashboard",220,310,250,function():void {
            flash.net.navigateToURL(new URLRequest(serverBase.replace(/\/api\/$/,"")+"/admin.html"),"_blank");
         });
      }
