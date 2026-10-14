package com.ankamagames.boufbowl.resolution.display.script.runner.action
{
   import com.ankamagames.boufbowl.resolution.display.script.runner.ISceneController;
   import com.ankamagames.boufbowl.utils.ControlledMovieClipFromResource;
   import com.ankamagames.boufbowl.utils.FrameController;
   import flash.events.Event;
   
   public class PlayMovieAction extends BaseAction
   {
      
      private var _movieName:String;
      
      private var _duration:int;
      
      private var _align:int;
      
      private var _realTime:Boolean;
      
      private var _isFlipped:Boolean;
      
      private var _frameController:FrameController;
      
      private var _controlledMovieClip:ControlledMovieClipFromResource;
      
      public function PlayMovieAction(param1:String, param2:int, param3:int, param4:Boolean, param5:Boolean)
      {
         super();
         this._movieName = param1;
         this._duration = param2;
         this._align = param3;
         this._realTime = param4;
         this._isFlipped = param5;
      }
      
      override public function toString() : String
      {
         return "PlayMovieAction{_movieName:\"" + this._movieName + "\", _duration:" + this._duration + "}";
      }
      
      override public function execute(param1:ISceneController) : void
      {
         super.execute(param1);
         try
         {
         var _loc2_:int = this._realTime ? param1.updateRealTime : param1.updateGameTime;
         this._frameController = new FrameController(_loc2_,this._duration,this._realTime);
         this._controlledMovieClip = new ControlledMovieClipFromResource(this._frameController,this._movieName,uiController.presenter.registry,param1.assetsConfig.moviesFile);
         if(this._isFlipped)
         {
            this._controlledMovieClip.movieClip.scaleX *= -1;
         }
         uiController.presenter.addSprite(this._controlledMovieClip.movieClip,this._align);
         param1.addUpdatable(this._frameController);
         this._frameController.addEventListener(FrameController.LAST_FRAME_REACHED,this.lastFrameReached);
         }
         catch(error:Error)
         {
            com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Movie unavailable: " + this._movieName + " - " + error.toString());
            if(this._controlledMovieClip != null) uiController.presenter.removeSprite(this._controlledMovieClip.movieClip);
            if(this._frameController != null) param1.removeUpdatable(this._frameController);
            this._controlledMovieClip=null; this._frameController=null;
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
         done();
      }
   }
}

