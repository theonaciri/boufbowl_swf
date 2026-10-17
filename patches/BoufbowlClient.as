package com.ankamagames.boufbowl
{
   import com.ankamagames.boufbowl.client.application.MainApp;
   import com.ankamagames.boufbowl.client.logging.UncaughtErrorsHandler;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.reider.log4AS3.ILogger;
   import com.reider.log4AS3.manager.LogManager;
   import flash.display.Sprite;
   import flash.display.StageAlign;
   import flash.display.StageScaleMode;
   import flash.events.Event;
   import flash.events.UncaughtErrorEvent;
   import flash.net.SharedObject;
   import flash.text.TextField;
   import flash.text.TextFormat;
   import flash.text.Font;
   
   [SWF(width="1024", height="600", backgroundColor="#000000", frameRate="25")]
   public class BoufbowlClient extends Sprite
   {
      
      private static var embeddedVersionClass:Class = BoufbowlClient_embeddedVersionClass;
      
      private static const LOGGER:ILogger = LoggerFactory.getLogger(BoufbowlClient);
      
      private var _uncaughtErrorsHandler:UncaughtErrorsHandler;
      
      public function BoufbowlClient()
      {
         super();
         LogManager.logFileURL = "../resources/logback.xml";
         LogManager(LogManager.getInstance()).init();
         this._uncaughtErrorsHandler = new UncaughtErrorsHandler(loaderInfo.uncaughtErrorEvents);
         loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,function(event:UncaughtErrorEvent):void {
            var diagnostic:TextField = new TextField();
            diagnostic.defaultTextFormat = new TextFormat("_sans",16,0xff6666);
            diagnostic.text = String(event.error);
            diagnostic.wordWrap = true;
            diagnostic.multiline = true;
            if(event.error is Error && Error(event.error).getStackTrace() != null) diagnostic.appendText("\n" + Error(event.error).getStackTrace());
            diagnostic.width = 1024;
            diagnostic.height = 500;
            if(stage != null) stage.addChild(diagnostic);
         });
         LOGGER.info("Starting up");
         this.logAvailableFonts();
         if(stage != null)
         {
            this.init();
         }
         else
         {
            addEventListener(Event.ADDED_TO_STAGE,this.addedToStageHandler,false,0,true);
         }
      }
      
      private function logAvailableFonts() : void
      {
         var _loc2_:Font = null;
         LOGGER.info("Available fonts :");
         var _loc1_:Array = Font.enumerateFonts();
         for each(_loc2_ in _loc1_)
         {
            LOGGER.info(" > fontName = " + _loc2_.fontName + ", fontStyle = " + _loc2_.fontStyle + ", fontType = " + _loc2_.fontType);
         }
      }
      
      private function init() : void
      {
         stage.align = StageAlign.TOP;
         stage.scaleMode = StageScaleMode.SHOW_ALL;
         var preferences:SharedObject = SharedObject.getLocal("BoufbowlPreferences","/");
         var frameRateTarget:Number = Number(preferences.data.frameRateTarget);
         if(isNaN(frameRateTarget) || frameRateTarget < 25 || frameRateTarget > 240)
         {
            frameRateTarget = Boolean(preferences.data.limitFrameRate25) ? 25 : 240;
         }
         stage.frameRate = frameRateTarget;
         addChild(new MainApp(this._uncaughtErrorsHandler,String(new embeddedVersionClass())));
      }
      
      private function addedToStageHandler(param1:Event) : void
      {
         removeEventListener(Event.ADDED_TO_STAGE,this.addedToStageHandler);
         this.init();
      }
   }
}

