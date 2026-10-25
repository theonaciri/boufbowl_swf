package com.ankamagames.boufbowl.match.strategic.boufbowler
{
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.utils.getTimer;

   public dynamic class ClassOrderIndicatorUI extends MovieClip
   {
      private var _startedAt:int;

      public function ClassOrderIndicatorUI()
      {
         super();
         gotoAndStop(1);
         addEventListener(Event.ADDED_TO_STAGE,this.addedToStage,false,0,true);
         addEventListener(Event.REMOVED_FROM_STAGE,this.removedFromStage,false,0,true);
      }

      private function addedToStage(event:Event) : void
      {
         this._startedAt = getTimer();
         addEventListener(Event.ENTER_FRAME,this.updateAnimation,false,0,true);
      }

      private function removedFromStage(event:Event) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.updateAnimation);
      }

      private function updateAnimation(event:Event) : void
      {
         if(!visible) return;
         // Original 14-frame loop: 560ms at its authored 25FPS cadence.
         var elapsed:int = Math.max(0,getTimer() - this._startedAt);
         var frame:int = 1 + Math.floor(elapsed * 25 / 1000) % totalFrames;
         if(currentFrame != frame) gotoAndStop(frame);
      }
   }
}
