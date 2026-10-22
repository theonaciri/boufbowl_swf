package com.ankamagames.boufbowl.client.match.resolution.view
{
   import com.ankamagames.boufbowl.client.match.model.MatchModel;
   import com.ankamagames.boufbowl.client.match.resolution.controller.PlayScriptEvent;
   import com.ankamagames.boufbowl.resolution.display.script.runner.ISceneController;
   import com.ankamagames.boufbowl.resolution.display.script.runner.IScriptRunner;
   import com.ankamagames.boufbowl.resolution.display.script.runner.ScriptRunner;
   import com.ankamagames.xgaming.utils.display.stage.IStageWrapper;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.reider.log4AS3.ILogger;
   import flash.events.Event;
   import org.robotlegs.mvcs.Mediator;

   public class ResolutionMediator extends Mediator
   {

      public static const SCRIPT_ENDED:String = "com.ankamagames.boufbowl.client.match.resolution.view.ResolutionMediator.SCRIPT_ENDED";

      private static const STANDARD_FPS:int = 25;

      private static const RESOLUTION_FPS:int = 50;

      private static const LOGGER:ILogger = LoggerFactory.getLogger(ResolutionMediator);

      private var _sceneController:ISceneController;

      private var _stage:IStageWrapper;

      private var _view:ResolutionView;

      private var _currentRunner:IScriptRunner;

      public function ResolutionMediator(param1:ISceneController, param2:IStageWrapper, param3:ResolutionView)
      {
         super();
         this._sceneController = param1;
         this._stage = param2;
         this._view = param3;
      }

      override public function onRegister() : void
      {
         super.onRegister();
         addContextListener(MatchModel.PLAY_SCRIPT,this.playScript);
         this._stage.frameRate = com.ankamagames.boufbowl.BoufbowlClient.ruffleRuntime ?
            com.ankamagames.boufbowl.BoufbowlClient.browserFrameRate :
            (com.ankamagames.boufbowl.BoufbowlClient.preferredFrameRate > 0 ?
               Math.min(RESOLUTION_FPS,com.ankamagames.boufbowl.BoufbowlClient.preferredFrameRate) : RESOLUTION_FPS);
      }

      override public function onRemove() : void
      {
         super.onRemove();
         if(this._currentRunner != null)
         {
            LOGGER.debug("Mediator::onRemove called with a script running. Cleaning...");
            this.cleanScript();
         }
         this._stage.frameRate = com.ankamagames.boufbowl.BoufbowlClient.ruffleRuntime ?
            com.ankamagames.boufbowl.BoufbowlClient.browserFrameRate :
            (com.ankamagames.boufbowl.BoufbowlClient.preferredFrameRate > 0 ?
               Math.min(STANDARD_FPS,com.ankamagames.boufbowl.BoufbowlClient.preferredFrameRate) : STANDARD_FPS);
         this._stage = null;
      }

      private function playScript(param1:PlayScriptEvent) : void
      {
         if(this._currentRunner != null)
         {
            LOGGER.warn("There\'s already a script running. Cleaning... (this should not happen)");
            this.cleanScript();
         }
         this._currentRunner = new ScriptRunner(param1.tree,this._sceneController);
         LOGGER.debug("Running {}",param1.tree.toString());
         this._sceneController.endCallback = this.scriptEnded;
         this._sceneController.addUpdatable(this._currentRunner);
         this._sceneController.update();
         this._view.sceneController = this._sceneController;
      }

      private function scriptEnded() : void
      {
         LOGGER.debug("Script end triggered. Cleaning.");
         this.cleanScript();
         dispatch(new Event(SCRIPT_ENDED));
      }

      private function cleanScript() : void
      {
         this._sceneController.endCallback = null;
         this._sceneController.reset();
         this._currentRunner.destroy();
         this._currentRunner = null;
         this._view.sceneController = null;
      }
   }
}
