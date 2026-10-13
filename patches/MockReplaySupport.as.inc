      // Opt-in protocol fixture harness. Included in configured startup patches.
      private static var mockActive:Boolean = false;
      private static var mockGeneration:int = 0;
      private static var mockFixture:Object;
      private static var mockIndex:int = 0;
      private static var mockWaiting:String;
      private static var mockTimer:uint;
      private static var mockTimeout:uint;
      private static var mockLabel:TextField;
      private static var mockTraceIndex:uint = 0;

      private static function startMock() : void
      {
         stopMock();
         mockActive = true;
         var generation:int = mockGeneration;
         mockStatus("Loading scripted protocol fixture");
         var loader:URLLoader = new URLLoader();
         loader.addEventListener(Event.COMPLETE,function(event:Event):void {
            if(!mockActive || generation != mockGeneration) return;
            try
            {
               mockFixture = com.adobe.serialization.json.JSON.decode(String(loader.data));
               if(mockFixture.format_version != 1 || !(mockFixture.steps is Array))
                  throw new Error("Unsupported mock fixture");
               mockIndex = 0;
               scheduleMockStep();
            }
            catch(error:Error) { mockFailure(error.toString()); }
         });
         loader.addEventListener(IOErrorEvent.IO_ERROR,function(event:IOErrorEvent):void {
            if(mockActive && generation == mockGeneration) mockFailure(event.text);
         });
         loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR,function(event:SecurityErrorEvent):void {
            if(mockActive && generation == mockGeneration) mockFailure(event.text);
         });
         loader.load(new URLRequest(@FIXTURE_URL@));
      }

      private static function stopMock() : void
      {
         mockGeneration++;
         mockActive = false;
         mockWaiting = null;
         clearTimeout(mockTimer);
         clearTimeout(mockTimeout);
         if(mockLabel != null && mockLabel.parent != null) mockLabel.parent.removeChild(mockLabel);
      }

      private static function mockStatus(text:String) : void
      {
         if(mockLabel == null)
         {
            mockLabel = new TextField();
            mockLabel.defaultTextFormat = new TextFormat("_sans",12,0xffff99);
            mockLabel.background = true;
            mockLabel.backgroundColor = 0x20252b;
            mockLabel.x = 10;
            mockLabel.y = 570;
            mockLabel.width = 512;
            mockLabel.height = 24;
            mockLabel.mouseEnabled = false;
         }
         mockLabel.width = Math.min(512,Stage(app.contextInjector.getInstance(Stage)).stageWidth / 2);
         mockLabel.wordWrap=true;
         mockLabel.text = "Replay: " + text;
         mockLabel.height=Math.min(72,mockLabel.textHeight+6);
         mockLabel.y=594-mockLabel.height;
         Stage(app.contextInjector.getInstance(Stage)).addChild(mockLabel);
         if(@TRACE_URL@ != "")
         {
            var traceLoader:URLLoader = new URLLoader();
            traceLoader.addEventListener(IOErrorEvent.IO_ERROR,function(event:IOErrorEvent):void {});
            traceLoader.addEventListener(SecurityErrorEvent.SECURITY_ERROR,function(event:SecurityErrorEvent):void {});
            traceLoader.load(new URLRequest(@TRACE_URL@ + "?event=" + encodeURIComponent(String(mockGeneration) + ":" + String(++mockTraceIndex) + ":" + String(getTimer()) + " " + text)));
         }
      }

      public static function mockPlaybackNotice(text:String) : void
      {
         if(mockActive) mockStatus(text);
      }

      private static function mockFailure(text:String) : void
      {
         clearTimeout(mockTimer);
         clearTimeout(mockTimeout);
         mockStatus("ERROR: " + text);
         mockActive = false;
      }

      private static function scheduleMockStep() : void
      {
         if(!mockActive || mockFixture == null) return;
         if(mockIndex >= mockFixture.steps.length)
         {
            mockStatus("Fixture delivered; match-end screen expected");
            return;
         }
         var step:Object = mockFixture.steps[mockIndex];
         if(step.wait_for != null)
         {
            mockWaiting = String(step.wait_for);
            mockStatus("Waiting for " + mockWaiting);
            mockTimeout = setTimeout(function():void {
               if(mockActive && mockWaiting != null) mockFailure("Timed out waiting for " + mockWaiting);
            },90000);
         }
         else mockTimer = setTimeout(deliverMockStep,int(step.after_ms));
      }

      private static function deliverMockStep() : void
      {
         if(!mockActive) return;
         try
         {
            var step:Object = mockFixture.steps[mockIndex];
            if(step.channel != "MATCH") throw new Error("Only MATCH fixture messages are supported");
            var hex:String = String(step.hex);
            if(hex.length == 0 || hex.length > 262144 || hex.length % 2 != 0 || /[^0-9a-f]/i.test(hex))
               throw new Error("Invalid protobuf fixture hex");
            var data:ByteArray = new ByteArray();
            for(var offset:int = 0;offset<hex.length;offset+=2) data.writeByte(parseInt(hex.substr(offset,2),16));
            data.position = 0;
            var message:BoufbowlMessage = new BoufbowlMessage();
            message.readExternal(data);
            mockIndex++;
            // Arm the next acknowledgement before dispatch: 2D playback may
            // finish synchronously, while 3D waits for animations to complete.
            scheduleMockStep();
            mockStatus("Incoming " + step.type + (mockWaiting != null ? "; waiting for " + mockWaiting : ""));
            var pipeline:ChannelPipeline = app.contextInjector.getInstance(ChannelPipeline,"MATCH");
            var handler:MatchMessageHandler = app.contextInjector.getInstance(MatchMessageHandler);
            pipeline.sendDataUpstream(message,handler);
         }
         catch(error:Error) { mockFailure(error.toString()); }
      }

      private static function mockOutgoing(request:Object) : void
      {
         var name:String = getQualifiedClassName(request).split("::").pop();
         mockStatus("Outgoing " + name);
         if(name == "SurrenderMessage" || name == "StopSpectatingMessage")
         {
            stopMock();
            showHome();
            return;
         }
         if(mockWaiting == name)
         {
            if(name == "ResolutionDoneMessage" && int(request.turn) != int(mockFixture.steps[mockIndex-1].decoded.turn))
            {
               mockFailure("Acknowledgement turn does not match fixture turn");
               return;
            }
            mockWaiting = null;
            clearTimeout(mockTimeout);
            mockTimer = setTimeout(deliverMockStep,int(mockFixture.steps[mockIndex].after_ms));
         }
      }
