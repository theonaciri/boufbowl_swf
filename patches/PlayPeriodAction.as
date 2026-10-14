package com.ankamagames.boufbowl.resolution.display.script.runner.action
{
   import as3.collections.IMap;
   import com.ankamagames.boufbowl.resolution.display.animation.BoufbowlerColorIndex;
   import com.ankamagames.boufbowl.resolution.display.cutscene.illustration.PeriodIllustration;
   import com.ankamagames.boufbowl.resolution.display.presenter.UIPresenter;
   import com.ankamagames.boufbowl.resolution.display.script.runner.ISceneController;
   import com.ankamagames.boufbowl.utils.ControlledMovieClipFromResource;
   import com.ankamagames.boufbowl.utils.FrameController;
   import com.ankamagames.xgaming.utils.collections.Collections;
   import com.ankamagames.xgaming.utils.display.Color3;
   import flash.events.Event;
   
   public class PlayPeriodAction extends BaseAction
   {
      
      private static const HAIR_COLORS:Array = [3354143,16707972,12162934,16776925,7795416,16750848,10665481,15544640];
      
      private static const EYES_COLORS:Array = [6386218,16675328,9206630,465950,3897962,3350802,13158,286596];
      
      private static const SKIN_COLORS:Array = [16764563,7490866,15903330,8022354,12554050,8537115,15384214,10785139];
      
      private var _periodName:String;
      
      private var _periodTitle:String;
      
      private var _teamColor:Color3;
      
      private var _frameController:FrameController;
      
      private var _controlledMovieClip:ControlledMovieClipFromResource;
      
      public function PlayPeriodAction(param1:String, param2:String, param3:Color3)
      {
         super();
         this._periodName = param1;
         this._periodTitle = param2;
         this._teamColor = param3;
      }
      
      override public function toString() : String
      {
         return "PlayPeriodAction{_periodName:\"" + this._periodName + "\", _periodTitle:" + this._periodTitle + "}";
      }
      
      override public function execute(param1:ISceneController) : void
      {
         super.execute(param1);
         try {
         var _loc2_:int = param1.updateGameTime;
         this._frameController = new FrameController(_loc2_);
         this._controlledMovieClip = new ControlledMovieClipFromResource(this._frameController,this._periodName,uiController.presenter.registry,param1.assetsConfig.pomPomGirlCutscenesFile);
         var _loc3_:IMap = Collections.map(1,this.createRandomColorGroup(),2,this.createRandomColorGroup());
         var _loc4_:PeriodIllustration = PeriodIllustration(this._controlledMovieClip.movieClip);
         _loc4_.applyColorGroups(_loc3_);
         _loc4_.title = this._periodTitle;
         uiController.presenter.addSprite(this._controlledMovieClip.movieClip,UIPresenter.ALIGN_CENTER);
         param1.addUpdatable(this._frameController);
         this._frameController.addEventListener(FrameController.LAST_FRAME_REACHED,this.lastFrameReached);
         com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Cinematic started: " + this._periodName + " / " + this._periodTitle);
         } catch(error:Error) {
            com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Cinematic unavailable: " + this._periodName + " / " + error.message);
            done();
         }
      }
      
      private function lastFrameReached(param1:Event) : void
      {
         this._frameController.removeEventListener(FrameController.LAST_FRAME_REACHED,this.lastFrameReached);
         uiController.presenter.removeSprite(this._controlledMovieClip.movieClip);
         sceneController.removeUpdatable(this._frameController);
         this._frameController = null;
         this._controlledMovieClip = null;
         com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Cinematic finished: " + this._periodName);
         done();
      }
      
      private function createRandomColorGroup() : IMap
      {
         return Collections.map(BoufbowlerColorIndex.HAIR,this.getRandomColor(HAIR_COLORS),BoufbowlerColorIndex.EYES,this.getRandomColor(EYES_COLORS),BoufbowlerColorIndex.SKIN,this.getRandomColor(SKIN_COLORS),BoufbowlerColorIndex.SHIRT,this._teamColor,BoufbowlerColorIndex.TROUSER,this._teamColor);
      }
      
      private function getRandomColor(param1:Array) : Color3
      {
         return Color3.fromRgbUInt(param1[uint(param1.length * Math.random())]);
      }
   }
}

