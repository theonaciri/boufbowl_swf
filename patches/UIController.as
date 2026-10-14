package com.ankamagames.boufbowl.resolution.display.script.runner
{
   import as3.collections.ArrayList;
   import as3.collections.IArrayList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.boufbowl.resolution.display.animation.IBoufbowlerSprite;
   import com.ankamagames.boufbowl.resolution.display.cutscene.CutSceneController;
   import com.ankamagames.boufbowl.resolution.display.cutscene.illustration.BoufbowlerIllustration;
   import com.ankamagames.boufbowl.resolution.display.presenter.IUIPresenter;
   import com.ankamagames.boufbowl.resolution.display.presenter.UIPresenter;
   import com.ankamagames.boufbowl.utils.ControlledMovieClipFromResource;
   import com.ankamagames.boufbowl.utils.FrameController;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.netease.protobuf.Int64;
   import com.reider.log4AS3.ILogger;
   
   public class UIController implements IUIController
   {
      
      private static var LOGGER:ILogger = LoggerFactory.getLogger(UIController);
      
      private var _presenter:IUIPresenter;
      
      private var _assetsConfig:IBoufbowlConfig;
      
      private var _cutSceneController:CutSceneController;
      
      private var _cutSceneBoufbowlerIllustration:BoufbowlerIllustration;
      
      private var _cutSceneControlledMovieClip:ControlledMovieClipFromResource;
      
      private var _playCutSceneDoneCallback:Function;
      
      public function UIController(param1:IUIPresenter, param2:IBoufbowlConfig)
      {
         super();
         this._presenter = param1;
         this._assetsConfig = param2;
      }
      
      public function get presenter() : IUIPresenter
      {
         return this._presenter;
      }
      
      public function reset() : void
      {
         this.resetCutScene();
         this._presenter.reset();
      }
      
      public function update(param1:int, param2:int) : void
      {
         this.updateCutScene(param1,param2);
      }
      
      public function playCutScene(param1:int, param2:String, param3:Boolean, param4:IArrayList, param5:Int64, param6:Boolean, param7:ISceneController, param8:Function = null) : void
      {
         var _loc10_:IBoufbowlerSprite = null;
         this.playCutSceneComplete();
         this._playCutSceneDoneCallback = param8;
         try
         {
         var _loc9_:FrameController = new FrameController(param1,-1,true,true);
         this._cutSceneControlledMovieClip = new ControlledMovieClipFromResource(_loc9_,param2,this.presenter.registry,param3 ? this._assetsConfig.illustrationCutscenesFile : this._assetsConfig.animatedCutscenesFile);
         if(param6)
         {
            this._cutSceneControlledMovieClip.movieClip.scaleX *= -1;
         }
         if(param3)
         {
            this._cutSceneBoufbowlerIllustration = this._cutSceneControlledMovieClip.movieClip as BoufbowlerIllustration;
            _loc10_ = _loc10_ == null ? null : param7.model.getBoufbowler(param5).sprite;
            this._cutSceneBoufbowlerIllustration.initFrom(this.buildBoufbowlersList(param4,param7),_loc10_);
         }
         else
         {
            this._cutSceneController = this._cutSceneControlledMovieClip.movieClip as CutSceneController;
            this._cutSceneController.registerBoufbowlers(param4,param7);
         }
         this.presenter.addSprite(this._cutSceneControlledMovieClip.movieClip,UIPresenter.ALIGN_CENTER);
         com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Cinematic started: " + param2);
         }
         catch(error:Error)
         {
            com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Cinematic unavailable: " + param2 + " - " + error.toString());
            this.resetCutScene();
            this.playCutSceneComplete();
         }
      }
      
      private function buildBoufbowlersList(param1:IArrayList, param2:ISceneController) : IArrayList
      {
         var _loc5_:Int64 = null;
         var _loc6_:IBoufbowlerSprite = null;
         var _loc3_:IArrayList = new ArrayList();
         var _loc4_:IIterator = param1.getIterator();
         while(_loc4_.hasNext())
         {
            _loc5_ = _loc4_.getNext();
            _loc6_ = param2.model.getBoufbowler(_loc5_).sprite;
            _loc3_.addItem(_loc6_);
         }
         return _loc3_;
      }
      
      private function updateCutScene(param1:int, param2:int) : void
      {
         if(this._cutSceneControlledMovieClip == null)
         {
            return;
         }
         this._cutSceneControlledMovieClip.frameController.update(param1,param2);
         if(this._cutSceneControlledMovieClip.frameController.lastFrameReached)
         {
            com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Cinematic finished");
            this.resetCutScene();
            this.playCutSceneComplete();
         }
      }
      
      private function resetCutScene() : void
      {
         if(this._cutSceneControlledMovieClip == null)
         {
            return;
         }
         if(this._cutSceneController != null)
         {
            this._cutSceneController.destroy();
         }
         this.presenter.removeSprite(this._cutSceneControlledMovieClip.movieClip);
         this._cutSceneController = null;
         this._cutSceneBoufbowlerIllustration = null;
         this._cutSceneControlledMovieClip = null;
      }
      
      private function playCutSceneComplete() : void
      {
         if(this._playCutSceneDoneCallback == null)
         {
            return;
         }
         var _loc1_:Function = this._playCutSceneDoneCallback;
         this._playCutSceneDoneCallback = null;
         _loc1_();
      }
   }
}

