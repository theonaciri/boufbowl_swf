package com.ankamagames.boufbowl.resolution.display.script.runner
{
   import as3.collections.IList;
   import as3.collections.LinkedList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.boufbowl.resolution.display.animation.TiphonProxy;
   import com.ankamagames.boufbowl.resolution.display.model.IBoufbowler;
   import com.ankamagames.boufbowl.resolution.display.model.IUpdatable;
   import com.ankamagames.boufbowl.resolution.display.model.SceneModel;
   import com.ankamagames.boufbowl.resolution.display.presenter.IScenePresenter;
   import com.ankamagames.xgaming.audio.controller.IAudioController;
   import com.ankamagames.xgaming.audio.controller.data.AudioRequest;
   import com.ankamagames.xgaming.audio.controller.data.VolumeData;
   import com.ankamagames.xgaming.utils.math.geom.Point2;
   import com.ankamagames.xgaming.utils.tween.ITweener;
   import com.ankamagames.xgaming.utils.tween.Point2Tweener;
   import com.ankamagames.xgaming.utils.tween.easing.Cubic;
   
   public class SceneController implements ISceneController
   {
      
      public static var active:SceneController;
      public function applyReplayTiming():void { this._tiphonProxy.slowAnimations(AsvmTimeProvider.replayPaused ? 0 : this.speed * AsvmTimeProvider.replayMultiplier); }
      private var _model:SceneModel;
      
      private var _presenter:IScenePresenter;
      
      private var _uiController:IUIController;
      
      private var _timeProvider:ITimeProvider;
      
      private var _tiphonProxy:TiphonProxy;
      
      private var _audioController:IAudioController;
      
      private var _config:IBoufbowlConfig;
      
      private var _savedSpeed:Number;
      
      private var _gamePaused:Boolean;
      
      private var _updatables:IList;
      
      private var _currentTime:int = -1;
      
      private var _realTime:int = -1;
      
      private var _sceneViewTweener:ITweener;
      
      private var _sceneViewMoveDoneCallback:Function;
      
      private var _endCallback:Function;
      
      public function SceneController(param1:SceneModel, param2:IScenePresenter, param3:ITimeProvider, param4:TiphonProxy, param5:IAudioController, param6:IUIController, param7:IBoufbowlConfig)
      {
         super();
         this._model = param1;
         this._presenter = param2;
         this._timeProvider = param3;
         this._tiphonProxy = param4;
         this._audioController = param5;
         this._config = param7;
         this._updatables = new LinkedList();
         this._updatables.addItem(param6);
         this._uiController = param6;
         active=this;this.applyReplayTiming();
      }
      
      public function get model() : SceneModel
      {
         return this._model;
      }
      
      public function get uiController() : IUIController
      {
         return this._uiController;
      }
      
      public function get audioController() : IAudioController
      {
         return this._audioController;
      }
      
      public function get assetsConfig() : IBoufbowlConfig
      {
         return this._config;
      }
      
      public function get updateGameTime() : int
      {
         return this._currentTime;
      }
      
      public function get updateRealTime() : int
      {
         return this._realTime;
      }
      
      public function get paused() : Boolean
      {
         return this._timeProvider.paused;
      }
      
      public function set paused(param1:Boolean) : void
      {
         this._timeProvider.paused = param1;
         if(this._timeProvider.paused)
         {
            if(!this._gamePaused)
            {
               this._savedSpeed = this._timeProvider.speed;
            }
            this._tiphonProxy.slowAnimations(0);
         }
         else
         {
            this._tiphonProxy.slowAnimations(this._savedSpeed);
         }
      }
      
      public function get speed() : Number
      {
         return this._timeProvider.speed;
      }
      
      public function set speed(param1:Number) : void
      {
         if(!this._gamePaused)
         {
            this._timeProvider.speed = param1;
         }
         this._tiphonProxy.slowAnimations(AsvmTimeProvider.replayPaused ? 0 : param1 * AsvmTimeProvider.replayMultiplier);
      }
      
      public function set endCallback(param1:Function) : void
      {
         this._endCallback = param1;
      }
      
      public function playSound(param1:String, param2:AudioRequest) : void
      {
         param2.url.url = this._config.soundBasePath + param2.url.url;
         this._audioController.playSound(param1,param2);
      }
      
      public function stopAllSounds(param1:String, param2:uint = 0) : void
      {
         this._audioController.fadeOutAllSounds(param1,param2);
      }
      
      public function setVolume(param1:String, param2:Number) : void
      {
         this._audioController.setVolume(param1,new VolumeData(param2));
      }
      
      public function pauseGame(param1:Number) : void
      {
         if(param1 > 0)
         {
            this._gamePaused = false;
            this._timeProvider.speed = param1;
         }
         else
         {
            this._gamePaused = true;
            this._savedSpeed = this._timeProvider.speed;
            this._timeProvider.speed = 0;
         }
      }
      
      public function highlight(param1:IBoufbowler, param2:Number) : void
      {
         this._presenter.highlightBoufbowler(param1,param2);
      }
      
      public function unhighlight(param1:IBoufbowler) : void
      {
         this._presenter.unhighlightBoufbowler(param1);
      }
      
      public function addUpdatable(param1:IUpdatable) : void
      {
         this._updatables.addItem(param1);
      }
      
      public function removeUpdatable(param1:IUpdatable) : void
      {
         this._updatables.removeAll(param1);
      }
      
      public function update() : void
      {
         var _loc2_:IUpdatable = null;
         this._currentTime = this._timeProvider.current;
         this._realTime = this._timeProvider.realTime;
         this._uiController.update(this._currentTime,this._realTime);
         var _loc1_:IIterator = this._updatables.getIterator();
         while(_loc1_.hasNext())
         {
            _loc2_ = IUpdatable(_loc1_.getNext());
            _loc2_.update(this._currentTime,this._realTime);
         }
         this._model.update(this._currentTime,this._realTime);
         this.updateSceneViewMove(this._realTime);
      }
      
      public function reset() : void
      {
         this._updatables.clear();
         this._model.removeAllBoufbowlerFxs();
         this._uiController.reset();
         this._presenter.reset();
         this._sceneViewTweener = null;
         this._sceneViewMoveDoneCallback = null;
         this.speed = 1;
      }
      
      public function moveSceneViewByFromCenter(param1:int, param2:Number, param3:Number, param4:Number, param5:Function = null) : void
      {
         this.sceneViewMoveComplete();
         this._sceneViewMoveDoneCallback = param5;
         if(param4 == 0)
         {
            this._presenter.sceneViewCenterOffset = new Point2(param2,param3);
            this._sceneViewTweener = null;
            this.sceneViewMoveComplete();
         }
         this._sceneViewTweener = new Point2Tweener(param1,this._presenter.sceneViewCenterOffset,param1 + param4,new Point2(param2,param3),Cubic.easeInOut);
      }
      
      public function end() : void
      {
         this._endCallback();
      }
      
      private function updateSceneViewMove(param1:int) : void
      {
         if(this._sceneViewTweener == null)
         {
            return;
         }
         this._presenter.sceneViewCenterOffset = this._sceneViewTweener.getValue(param1) as Point2;
         if(this._sceneViewTweener.complete)
         {
            this._sceneViewTweener = null;
            this.sceneViewMoveComplete();
         }
      }
      
      private function sceneViewMoveComplete() : void
      {
         if(this._sceneViewMoveDoneCallback == null)
         {
            return;
         }
         var _loc1_:Function = this._sceneViewMoveDoneCallback;
         this._sceneViewMoveDoneCallback = null;
         _loc1_();
      }
   }
}

