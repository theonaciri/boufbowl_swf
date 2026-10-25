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
   import flash.events.IEventDispatcher;
   import flash.events.TouchEvent;
   import flash.events.UncaughtErrorEvent;
   import flash.geom.Point;
   import flash.media.SoundMixer;
   import flash.media.SoundTransform;
   import flash.net.SharedObject;
   import flash.ui.Multitouch;
   import flash.ui.MultitouchInputMode;
   import flash.utils.Dictionary;
   import flash.utils.getDefinitionByName;
   import flash.text.Font;
   import flash.text.TextField;
   import flash.text.TextFormat;
   
   [SWF(width="1024", height="600", backgroundColor="#000000", frameRate="25")]
   [SWF(frameRate="25",backgroundColor="#000000",width="1024",height="600")]
   public class BoufbowlClient extends Sprite
   {
      // @shared-client-runtime

      private static var embeddedVersionClass:Class = BoufbowlClient_embeddedVersionClass;
      
      private static var LOGGER:ILogger;
      
      private var _startupPhase:String = "document constructor";
      private var _startupDiagnostic:TextField;
      private var _uncaughtErrorsHandler:UncaughtErrorsHandler;
      private var _gameView:Sprite;
      private var _touchPoints:Dictionary = new Dictionary();
      private var _pinching:Boolean = false;
      private var _zoom:Number = 1;
      private var _minimumZoom:Number = 1;
      private var _maximumZoom:Number = 8;
      private var _backgroundSoundTransform:SoundTransform;
      
      public function BoufbowlClient()
      {
         super();
         loaderInfo.uncaughtErrorEvents.addEventListener(UncaughtErrorEvent.UNCAUGHT_ERROR,this.startupErrorHandler,false,1000);
         // Resolve AIR's application singleton at runtime: FFDec's shared
         // compiler globals also serve the non-AIR desktop client.
         var nativeApplicationClass:Class = getDefinitionByName("flash.desktop.NativeApplication") as Class;
         var lifecycle:IEventDispatcher = nativeApplicationClass["nativeApplication"] as IEventDispatcher;
         lifecycle.addEventListener(Event.DEACTIVATE,this.backgroundAudio,false,0,true);
         lifecycle.addEventListener(Event.ACTIVATE,this.foregroundAudio,false,0,true);
         if(stage != null)
         {
            this.startApplication();
         }
         else
         {
            addEventListener(Event.ADDED_TO_STAGE,this.addedToStageHandler,false,0,true);
         }
      }

      private function backgroundAudio(event:Event) : void
      {
         if(this._backgroundSoundTransform != null) return;
         this._backgroundSoundTransform = SoundMixer.soundTransform;
         var silent:SoundTransform = SoundMixer.soundTransform;
         silent.volume = 0;
         SoundMixer.soundTransform = silent;
      }

      private function foregroundAudio(event:Event) : void
      {
         if(this._backgroundSoundTransform == null) return;
         SoundMixer.soundTransform = this._backgroundSoundTransform;
         this._backgroundSoundTransform = null;
      }

      private function startupErrorHandler(event:UncaughtErrorEvent) : void
      {
         this.showStartupError(event.error);
      }

      private function showStartupError(error:Object) : void
      {
         if(this._startupDiagnostic == null) this._startupDiagnostic = new TextField();
         var diagnostic:TextField = this._startupDiagnostic;
         diagnostic.defaultTextFormat = new TextFormat("_sans",18,0xffffff);
         diagnostic.embedFonts = false;
         diagnostic.background = true;
         diagnostic.backgroundColor = 0x391b24;
         diagnostic.text = "Boufbowl Fan — " + (this._startupPhase == "game runtime" ? "erreur en jeu" : "démarrage interrompu") + "\nÉtape : " + this._startupPhase + "\n" + String(error);
         diagnostic.wordWrap = true;
         diagnostic.multiline = true;
         if(error is Error && Error(error).getStackTrace() != null)
         {
            diagnostic.appendText("\n" + Error(error).getStackTrace());
         }
         diagnostic.width = 1024;
         diagnostic.height = 600;
         if(stage != null) stage.addChild(diagnostic);
         else addChild(diagnostic);
      }

      private function startApplication() : void
      {
         try
         {
            this._startupPhase = "runtime policy";
            this.initializeClientRuntime(false);
            // Logging may load resources asynchronously. Install error handling
            // first and catch synchronous failures in this startup entry point.
            this._startupPhase = "logging configuration";
            LogManager.logFileURL = "app:/resources/logback.xml";
            LogManager(LogManager.getInstance()).init();
            this._startupPhase = "uncaught-error handler";
            this._uncaughtErrorsHandler = new UncaughtErrorsHandler(loaderInfo.uncaughtErrorEvents);
            this._startupPhase = "logger factory";
            LOGGER = LoggerFactory.getLogger(BoufbowlClient);
            LOGGER.info("Starting up");
            this._startupPhase = "font enumeration";
            this.logAvailableFonts();
            this.init();
         }
         catch(error:Error)
         {
            this.showStartupError(error);
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
         this._startupPhase = "stage setup";
         stage.align = StageAlign.TOP;
         stage.scaleMode = StageScaleMode.SHOW_ALL;
         this._startupPhase = "saved preferences";
         var preferences:SharedObject = SharedObject.getLocal("BoufbowlPreferences","/");
         stage.frameRate = this.restoreFrameRate(preferences.data);
         this._startupPhase = "touch setup";
         Multitouch.inputMode = MultitouchInputMode.TOUCH_POINT;
         this._gameView = new Sprite();
         addChild(this._gameView);
         this._startupPhase = "embedded version";
         var embeddedVersion:String = String(new embeddedVersionClass());
         this._startupPhase = "MainApp constructor";
         var application:MainApp = new MainApp(this._uncaughtErrorsHandler,embeddedVersion);
         this._startupPhase = "MainApp configuration/context startup";
         this._gameView.addChild(application);
         stage.addEventListener(TouchEvent.TOUCH_BEGIN,this.onTouchBegin,true,1000);
         stage.addEventListener(TouchEvent.TOUCH_MOVE,this.onTouchMove,true,1000);
         stage.addEventListener(TouchEvent.TOUCH_END,this.onTouchEnd,true,1000);
         this._startupPhase = "game runtime";
      }

      private function onTouchBegin(event:TouchEvent) : void
      {
         this._touchPoints[event.touchPointID] = new Point(event.stageX,event.stageY);
         if(this.touchCount() >= 2)
         {
            this._pinching = true;
            event.stopImmediatePropagation();
         }
      }

      private function onTouchMove(event:TouchEvent) : void
      {
         if(this._touchPoints[event.touchPointID] == null)
         {
            return;
         }
         var previous:Point = this._touchPoints[event.touchPointID] as Point;
         var current:Point = new Point(event.stageX,event.stageY);
         if(this._pinching)
         {
            if(this.touchCount() >= 2)
            {
               var other:Point = this.otherTouch(event.touchPointID);
               if(other != null)
               {
                  var oldMidX:Number = (previous.x + other.x) / 2;
                  var oldMidY:Number = (previous.y + other.y) / 2;
                  var newMidX:Number = (current.x + other.x) / 2;
                  var newMidY:Number = (current.y + other.y) / 2;
                  var oldDistance:Number = Point.distance(previous,other);
                  var newDistance:Number = Point.distance(current,other);
                  if(oldDistance > 0)
                  {
                     var localAnchor:Point = this._gameView.globalToLocal(new Point(oldMidX,oldMidY));
                     this._zoom = Math.max(this._minimumZoom,Math.min(this._maximumZoom,this._zoom * newDistance / oldDistance));
                     if(this._zoom >= 0.95 && this._zoom <= 1.05)
                     {
                        this._zoom = 1;
                     }
                     this._gameView.scaleX = this._zoom;
                     this._gameView.scaleY = this._zoom;
                     this._gameView.x = this._zoom == 1 ? 0 : Math.max(1024 * (1 - this._zoom),Math.min(0,newMidX - localAnchor.x * this._zoom));
                     this._gameView.y = this._zoom == 1 ? 0 : Math.max(600 * (1 - this._zoom),Math.min(0,newMidY - localAnchor.y * this._zoom));
                  }
               }
            }
            event.stopImmediatePropagation();
         }
         this._touchPoints[event.touchPointID] = current;
      }

      private function onTouchEnd(event:TouchEvent) : void
      {
         if(this._pinching)
         {
            event.stopImmediatePropagation();
         }
         delete this._touchPoints[event.touchPointID];
         if(this.touchCount() == 0)
         {
            this._pinching = false;
         }
      }

      private function touchCount() : int
      {
         var count:int = 0;
         for each(var point:Point in this._touchPoints)
         {
            count++;
         }
         return count;
      }

      private function otherTouch(touchPointID:int) : Point
      {
         for(var id:Object in this._touchPoints)
         {
            if(int(id) != touchPointID)
            {
               return this._touchPoints[id] as Point;
            }
         }
         return null;
      }
      
      private function addedToStageHandler(event:Event) : void
      {
         removeEventListener(Event.ADDED_TO_STAGE,this.addedToStageHandler);
         this.startApplication();
      }
   }
}

