package com.ankamagames.boufbowl.resolution.display.script.runner.action
{
   import com.ankamagames.boufbowl.resolution.display.cutscene.illustration.VersusIllustration;
   import com.ankamagames.boufbowl.resolution.display.model.ResolutionClubInformation;
   import com.ankamagames.boufbowl.resolution.display.presenter.UIPresenter;
   import com.ankamagames.boufbowl.resolution.display.script.runner.ISceneController;
   import com.ankamagames.boufbowl.utils.ControlledMovieClipFromResource;
   import com.ankamagames.boufbowl.utils.FrameController;
   import flash.events.Event;
   
   public class PlayVersusAction extends BaseAction
   {
      
      private var _leftResolutionClubInformation:ResolutionClubInformation;
      
      private var _rightResolutionClubInformation:ResolutionClubInformation;
      
      private var _controlledMovieClip:ControlledMovieClipFromResource;
      
      private var _frameController:FrameController;
      
      private var _clipName:String;
      
      public function PlayVersusAction(param1:String, param2:ResolutionClubInformation, param3:ResolutionClubInformation)
      {
         super();
         this._clipName = param1;
         this._leftResolutionClubInformation = param2;
         this._rightResolutionClubInformation = param3;
      }
      
      override public function execute(param1:ISceneController) : void
      {
         super.execute(param1);
         var _loc2_:int = param1.updateGameTime;
         this._frameController = new FrameController(_loc2_);
         this._controlledMovieClip = new ControlledMovieClipFromResource(this._frameController,this._clipName,uiController.presenter.registry,param1.assetsConfig.illustrationCutscenesFile);
         var _loc3_:VersusIllustration = VersusIllustration(this._controlledMovieClip.movieClip);
         this.initIllustration(_loc3_);
         uiController.presenter.addSprite(this._controlledMovieClip.movieClip,UIPresenter.ALIGN_CENTER);
         com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Versus cinematic started");
         param1.addUpdatable(this._frameController);
         this._frameController.addEventListener(FrameController.LAST_FRAME_REACHED,this.lastFrameReached);
      }
      
      private function lastFrameReached(param1:Event) : void
      {
         this._frameController.removeEventListener(FrameController.LAST_FRAME_REACHED,this.lastFrameReached);
         sceneController.removeUpdatable(this._frameController);
         this._frameController = null;
         this._controlledMovieClip = null;
         done();
      }
      
      private function initIllustration(param1:VersusIllustration) : void
      {
         param1.setLeftSigilIllustration(this._leftResolutionClubInformation.sigilIllustration);
         param1.setLeftBoufbowlerIllustration(this._leftResolutionClubInformation.boufbowlerIllustration);
         param1.setLeftClubName(this._leftResolutionClubInformation.name);
         param1.setLeftLeagueName(this._leftResolutionClubInformation.league);
         param1.setLeftRanking(this._leftResolutionClubInformation.ranking);
         param1.setRightSigilIllustration(this._rightResolutionClubInformation.sigilIllustration);
         param1.setRightBoufbowlerIllustration(this._rightResolutionClubInformation.boufbowlerIllustration);
         param1.setRightClubName(this._rightResolutionClubInformation.name);
         param1.setRightLeagueName(this._rightResolutionClubInformation.league);
         param1.setRightRanking(this._rightResolutionClubInformation.ranking);
      }
   }
}

