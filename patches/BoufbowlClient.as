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
   import flash.net.URLVariables;
   import flash.text.TextField;
   import flash.text.TextFormat;
   import flash.text.Font;
   import flash.utils.getTimer;
   
   [SWF(width="1920", height="1125", backgroundColor="#000000", frameRate="60")]
   public class BoufbowlClient extends Sprite
   {
      // @shared-client-runtime

      private static var embeddedVersionClass:Class = BoufbowlClient_embeddedVersionClass;
      
      private static const LOGGER:ILogger = LoggerFactory.getLogger(BoufbowlClient);
      
      private var _uncaughtErrorsHandler:UncaughtErrorsHandler;
      private var _fpsLabel:TextField;
      private var _fpsFrames:int = 0;
      private var _fpsWindowStart:int = 0;
      
      public function BoufbowlClient()
      {
         super();
         this.initializeClientRuntime(true);
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
            diagnostic.width = 1920;
            diagnostic.height = 1025;
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
         stage.frameRate = this.restoreFrameRate(preferences.data);
         if(ruffleRuntime)
         {
            if(flash.external.ExternalInterface.available)
               flash.external.ExternalInterface.addCallback("setWebDisplay",this.setWebDisplay);
         }
         addChild(new MainApp(this._uncaughtErrorsHandler,String(new embeddedVersionClass())));
         if(this.launchFlagEnabled("showFps"))
         {
            this.showFpsCounter();
         }
      }

      private function launchFlagEnabled(name:String) : Boolean
      {
         var parameters:Object = loaderInfo.parameters;
         var key:String = null;
         if(parameters != null)
         {
            for(key in parameters)
            {
               if(key.toLowerCase() == name.toLowerCase() && String(parameters[key]) == "1")
               {
                  return true;
               }
            }
         }
         var url:String = loaderInfo.url;
         var queryStart:int = url.indexOf("?");
         if(queryStart < 0)
         {
            return false;
         }
         var query:String = url.substr(queryStart + 1).split("#")[0];
         var variables:URLVariables = new URLVariables(query);
         for(key in variables)
         {
            if(key.toLowerCase() == name.toLowerCase() && String(variables[key]) == "1")
            {
               return true;
            }
         }
         return false;
      }

      private function setWebDisplay(fps:Number, quality:String) : Boolean
      {
         if(!ruffleRuntime || isNaN(fps) || fps < 25 || fps > 60 ||
            (quality != "low" && quality != "medium" && quality != "high")) return false;
         browserFrameRate = fps;
         stage.frameRate = fps;
         stage.quality = quality;
         return true;
      }

      private function showFpsCounter() : void
      {
         this._fpsLabel = new TextField();
         this._fpsLabel.defaultTextFormat = new TextFormat("_sans",14,16777215,true);
         this._fpsLabel.autoSize = "left";
         this._fpsLabel.background = true;
         this._fpsLabel.backgroundColor = 0;
         this._fpsLabel.alpha = 0.82;
         this._fpsLabel.selectable = false;
         this._fpsLabel.mouseEnabled = false;
         this._fpsLabel.x = 8;
         this._fpsLabel.y = 8;
         this._fpsLabel.text = "FPS: --";
         stage.addChild(this._fpsLabel);
         this._fpsWindowStart = getTimer();
         addEventListener(Event.ENTER_FRAME,this.updateFpsCounter,false,0,true);
      }

      private function updateFpsCounter(event:Event) : void
      {
         ++this._fpsFrames;
         var now:int = getTimer();
         var elapsed:int = now - this._fpsWindowStart;
         if(elapsed >= 500)
         {
            this._fpsLabel.text = "FPS: " + Math.round(this._fpsFrames * 1000 / elapsed);
            this._fpsFrames = 0;
            this._fpsWindowStart = now;
         }
      }
      
      private function addedToStageHandler(param1:Event) : void
      {
         removeEventListener(Event.ADDED_TO_STAGE,this.addedToStageHandler);
         this.init();
      }
   }
}

