package com.ankamagames.boufbowl.resolution.display.script.runner
{
   import flash.utils.getTimer;
   public class AsvmTimeProvider implements ITimeProvider
   {
      public static var replayMultiplier:Number = 1;
      public static var replayPaused:Boolean = false;
      private static var lastWall:int = getTimer();
      private static var virtualTime:Number = lastWall;
      public function AsvmTimeProvider() { super(); }
      private static function now() : int {
         var wall:int=getTimer();
         virtualTime += Math.max(0,wall-lastWall)*(replayPaused ? 0 : replayMultiplier);
         lastWall=wall;return int(virtualTime);
      }
      public static function configure(multiplier:Number,paused:Boolean) : void {
         now();replayMultiplier=multiplier;replayPaused=paused;
      }
      public function get current() : int { return now(); }
      public function get realTime() : int { return now(); }
      public function get speed() : Number { return 1; }
      public function set speed(value:Number) : void { }
      public function get paused() : Boolean { return replayPaused; }
      public function set paused(value:Boolean) : void { }
   }
}
