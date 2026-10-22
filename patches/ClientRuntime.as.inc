      // Generated into both roots; Android explicitly disables browser policies.
      public static var ruffleRuntime:Boolean = false;
      public static var browserFrameRate:Number = 30;
      public static var preferredFrameRate:Number = 0;

      private function initializeClientRuntime(allowBrowser:Boolean) : void
      {
         ruffleRuntime = allowBrowser && loaderInfo.parameters.clientRuntime == "ruffle";
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
