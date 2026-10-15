package com.ankamagames.boufbowl.client.ui
{
   import com.ankamagames.xgaming.ui.components.BaseComponent;
   import com.ankamagames.xgaming.ui.components.FlashInstanceContainer;
   import flash.events.Event;
   import flash.system.Capabilities;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol756")]
   public dynamic class SliderTrack extends BaseComponent
   {
      
      public function SliderTrack()
      {
         super();
         addFrameScript(0,this.frame1,1,this.frame2,2,this.frame3,3,this.frame4);
         if(Capabilities.playerType == "PlugIn")
            addEventListener(Event.ENTER_FRAME,this.browserTrackArtwork,false,0,true);
      }
      
      private function browserTrackArtwork(event:Event) : void
      {
         FlashInstanceContainer.repairBrowserSkin(this,true);
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

