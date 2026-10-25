package
{
   import com.ankamagames.xgaming.ui.components.Button;
   import flash.text.TextField;
   import flash.events.Event;
   import flash.display.DisplayObjectContainer;
   import flash.system.Capabilities;
   import com.ankamagames.xgaming.ui.components.FlashInstanceContainer;

   public dynamic class RunningButtonSprite extends Button
   {

      public var label:TextField;

      public function RunningButtonSprite()
      {
         super();
         addFrameScript(0,this.frame1,1,this.frame2,2,this.frame3,3,this.frame4);
         if(Capabilities.playerType == "PlugIn")
         {
            addEventListener(Event.ADDED_TO_STAGE,this.startBrowserSkin,false,0,true);
            addEventListener(Event.REMOVED_FROM_STAGE,this.stopBrowserSkin,false,0,true);
         }
      }

      private function startBrowserSkin(event:Event) : void
      {
         addEventListener(Event.ENTER_FRAME,this.updateBrowserSkin,false,0,true);
      }

      private function stopBrowserSkin(event:Event) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.updateBrowserSkin);
      }

      private function updateBrowserSkin(event:Event) : void
      {
         // Preserve the live label and original button hit target on every state.
         for(var index:int=0;index<numChildren;index++)
            if(getChildAt(index) is DisplayObjectContainer)
               FlashInstanceContainer.repairBrowserSkin(DisplayObjectContainer(getChildAt(index)),true);
      }

      internal function frame1() : *
      {
         stop();
      }

      internal function frame2() : *
      {
         stop();
      }

      internal function frame3() : *
      {
         stop();
      }

      internal function frame4() : *
      {
         stop();
      }
   }
}
