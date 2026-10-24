      // Generated into both roots; Android explicitly disables browser policies.
      public static var ruffleRuntime:Boolean = false;
      public static var browserFrameRate:Number = 30;
      public static var preferredFrameRate:Number = 0;

      private function initializeClientRuntime(allowBrowser:Boolean) : void
      {
         measurementRoot = this;
         measurementLaunchAt = getTimer();
         ruffleRuntime = allowBrowser && loaderInfo.parameters.clientRuntime == "ruffle";
         if(ruffleRuntime && flash.external.ExternalInterface.available)
            flash.external.ExternalInterface.addCallback("setMeasurementActive",setMeasurementActive);
         if(ruffleRuntime && loaderInfo.parameters.webFps != null)
         {
            var requested:Number = Number(loaderInfo.parameters.webFps);
            if(requested >= 25 && requested <= 60) browserFrameRate = requested;
         }
      }

      public static function readFrameRatePreference(preferences:Object) : Number
      {
         var requested:Number = Number(preferences.frameRateTarget);
         if(requested >= 25 && requested <= 240) return requested;
         return Boolean(preferences.limitFrameRate25) ? 25 : 0;
      }

      private function restoreFrameRate(preferences:Object) : Number
      {
         preferredFrameRate = readFrameRatePreference(preferences);
         return ruffleRuntime ? browserFrameRate : (preferredFrameRate > 0 ? preferredFrameRate : 60);
      }

      public static function sceneFrameRate(defaultRate:Number) : Number
      {
         return ruffleRuntime ? browserFrameRate :
            (preferredFrameRate > 0 ? Math.min(defaultRate,preferredFrameRate) : defaultRate);
      }

      private static var measurementRoot:BoufbowlClient;
      private static var measurementSink:Function;
      private static var measurementPhase:String = "ui";
      private static var measurementActive:Boolean = true;
      private static var measurementStartupReported:Boolean = false;
      private static var measurementLaunchAt:int;
      private static var measurementLast:int;
      private static var measurementFrames:int = 0;
      private static var measurementElapsed:Number = 0;
      private static var measurementSlow:int = 0;
      private static var measurementMax:Number = 0;
      private static var measurementTarget:Number = 30;
      private static var measurementHistogram:Array = [0,0,0,0,0,0,0,0,0,0];
      private static const MEASUREMENT_BUCKETS:Array = [8,17,25,34,50,67,100,250,1000,60000];

      public static function setRuntimeMeasurementSink(sink:Function) : void
      {
         if(measurementRoot == null || measurementRoot.stage == null) return;
         if((sink == null) == (measurementSink == null)) return;
         measurementSink = sink;
         measurementRoot.removeEventListener(Event.ENTER_FRAME,measureRuntimeFrame);
         measurementRoot.stage.removeEventListener(Event.ACTIVATE,measurementActivated);
         measurementRoot.stage.removeEventListener(Event.DEACTIVATE,measurementDeactivated);
         resetMeasurements();
         if(sink == null) return;
         measurementRoot.addEventListener(Event.ENTER_FRAME,measureRuntimeFrame,false,0,true);
         measurementRoot.stage.addEventListener(Event.ACTIVATE,measurementActivated,false,0,true);
         measurementRoot.stage.addEventListener(Event.DEACTIVATE,measurementDeactivated,false,0,true);
         if(!measurementStartupReported)
         {
            measurementStartupReported = true;
            var startupElapsed:int = getTimer()-measurementLaunchAt;
            if(startupElapsed >= 0 && startupElapsed <= 3600000)
               sink({kind:"game_startup",elapsed_ms:startupElapsed});
         }
      }

      public static function setMeasurementPhase(phase:String) : void
      {
         if(phase != "ui" && phase != "3d") return;
         if(phase == measurementPhase) return;
         flushMeasurements();
         measurementPhase = phase;
      }

      public static function setMeasurementActive(active:Boolean) : void
      {
         if(active == measurementActive) return;
         flushMeasurements();
         measurementActive = active;
         measurementLast = getTimer();
      }

      private static function measurementActivated(event:Event) : void { setMeasurementActive(true); }
      private static function measurementDeactivated(event:Event) : void { setMeasurementActive(false); }

      private static function resetMeasurements() : void
      {
         measurementLast = getTimer();
         measurementFrames = measurementSlow = 0;
         measurementElapsed = measurementMax = 0;
         measurementHistogram = [0,0,0,0,0,0,0,0,0,0];
         if(measurementRoot != null && measurementRoot.stage != null)
            measurementTarget = measurementRoot.stage.frameRate;
      }

      private static function measureRuntimeFrame(event:Event) : void
      {
         var now:int = getTimer();
         var elapsed:int = now-measurementLast;
         measurementLast = now;
         if(!measurementActive || elapsed <= 0 || elapsed > 60000) return;
         if(measurementRoot.stage.frameRate != measurementTarget) { flushMeasurements();return; }
         measurementFrames++;
         measurementElapsed += elapsed;
         measurementMax = Math.max(measurementMax,elapsed);
         if(elapsed > 2000/measurementTarget) measurementSlow++;
         var bucket:int = 0;
         while(bucket < MEASUREMENT_BUCKETS.length-1 && elapsed > MEASUREMENT_BUCKETS[bucket]) bucket++;
         measurementHistogram[bucket]++;
         if(measurementElapsed >= 30000) flushMeasurements();
      }

      private static function flushMeasurements() : void
      {
         if(measurementSink != null && measurementElapsed >= 1000 && measurementFrames > 0)
         {
            var memory:Object = null;
            try { if(flash.system.System.totalMemory > 0) memory = flash.system.System.totalMemory/1048576; } catch(ignored:Error) {}
            measurementSink({kind:"game_frames",phase:measurementPhase,frames:measurementFrames,
               elapsed_ms:measurementElapsed,slow_frames:measurementSlow,target_fps:measurementTarget,
               max_frame_ms:measurementMax,memory_mb:memory,histogram:measurementHistogram});
         }
         resetMeasurements();
      }
