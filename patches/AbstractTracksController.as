package com.ankamagames.xgaming.audio.controller
{
   import flash.net.SharedObject;
   import as3.collections.ArrayList;
   import as3.collections.IList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.xgaming.audio.controller.data.AudioRequest;
   import com.ankamagames.xgaming.audio.controller.data.VolumeData;
   import com.ankamagames.xgaming.audio.track.IAudioTrack;
   import com.ankamagames.xgaming.audio.track.IAudioTrackWithFadedLoops;
   import com.ankamagames.xgaming.audio.track.TracksCollection;
   import com.ankamagames.xgaming.utils.tween.NumberTweener;
   import com.ankamagames.xgaming.utils.tween.easing.Linear;
   
   public class AbstractTracksController implements ITracksController
   {
      
      private static var _controllers:Array = [];
      private static var _preferences:SharedObject;

      private static function preferences() : SharedObject
      {
         if(_preferences == null) _preferences = SharedObject.getLocal("BoufbowlPreferences","/");
         return _preferences;
      }

      private static function normalizedVolume(value:*) : Number
      {
         if(value == null || isNaN(Number(value))) return 1;
         return Math.max(0,Math.min(1,Number(value)));
      }

      public static function get fxVolume() : Number { return normalizedVolume(preferences().data.fxVolume); }
      public static function get musicVolume() : Number { return normalizedVolume(preferences().data.musicVolume); }

      public static function saveCategoryVolumes(fx:Number, music:Number) : void
      {
         preferences().data.fxVolume = normalizedVolume(fx);
         preferences().data.musicVolume = normalizedVolume(music);
         for each(var controller:AbstractTracksController in _controllers) controller.applyOwnVolumeToTracks();
         try { preferences().flush(); } catch(error:Error) {}
      }

      protected var _ownVolume:VolumeData;
      
      protected var _muted:Boolean;
      
      protected var _actualVolume:VolumeData;
      
      private var _controllerId:String;
      
      private var _fadeOutTweener:NumberTweener;
      
      private var _lastUpdateTime:int;
      
      private var _updatableTracks:IList;
      
      public function AbstractTracksController(param1:TracksCollection, param2:String)
      {
         super();
         this._controllerId = param2;
         this.init(param1);
         _controllers.push(this);
      }
      
      final public function get muted() : Boolean
      {
         return this._muted;
      }
      
      final public function set muted(param1:Boolean) : void
      {
         this._muted = param1;
         this.applyOwnVolumeToTracks();
      }
      
      final public function get volume() : VolumeData
      {
         return this._ownVolume;
      }
      
      final public function set volume(param1:VolumeData) : void
      {
         this._ownVolume = param1;
         this.applyOwnVolumeToTracks();
      }
      
      public function get controllerId() : String
      {
         return this._controllerId;
      }
      
      public function playSound(param1:AudioRequest) : void
      {
         throw new Error("Abstract method to override in sub-classes");
      }
      
      public function stopAllSounds() : void
      {
         throw new Error("Abstract method to override in sub-classes");
      }
      
      public function fadeOut(param1:uint) : void
      {
         if(param1 == 0)
         {
            this.stopAllSounds();
            return;
         }
         this._actualVolume = this._ownVolume;
         this._fadeOutTweener = new NumberTweener(this._lastUpdateTime,this._ownVolume.value,this._lastUpdateTime + param1,0,Linear.easeNone);
      }
      
      public function update(param1:int) : void
      {
         var _loc3_:Number = NaN;
         this._lastUpdateTime = param1;
         if(this._fadeOutTweener)
         {
            _loc3_ = Number(this._fadeOutTweener.getValue(this._lastUpdateTime));
            this.volume = new VolumeData(_loc3_);
            if(this._fadeOutTweener.complete)
            {
               this._fadeOutTweener = null;
               this.stopAllSounds();
               this.volume = this._actualVolume;
            }
         }
         var _loc2_:IIterator = this._updatableTracks.getIterator();
         while(_loc2_.hasNext())
         {
            IAudioTrackWithFadedLoops(_loc2_.getNext()).update(param1);
         }
      }
      
      protected function get lastUpdateTime() : int
      {
         return this._lastUpdateTime;
      }
      
      protected function applyOwnVolumeToTracks() : void
      {
         throw new Error("Abstract method to override in sub-classes");
      }
      
      protected function ownVolumeToTransmit() : VolumeData
      {
         return this._muted ? VolumeData.SILENCE : new VolumeData(this._ownVolume.value * (this._controllerId == "music" ? musicVolume : fxVolume));
      }
      
      private function init(param1:TracksCollection) : void
      {
         var _loc3_:IAudioTrack = null;
         this._ownVolume = VolumeData.FULL;
         this._muted = false;
         this._actualVolume = this._ownVolume;
         this._updatableTracks = new ArrayList();
         var _loc2_:IIterator = param1.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            _loc3_.parentControllerId = this._controllerId;
            if(_loc3_ is IAudioTrackWithFadedLoops)
            {
               this._updatableTracks.addItem(_loc3_);
            }
         }
      }
   }
}

