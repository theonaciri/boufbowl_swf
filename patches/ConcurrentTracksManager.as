package com.ankamagames.xgaming.audio.controller
{
   import as3.collections.ArrayList;
   import as3.collections.IArrayList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.xgaming.audio.controller.data.AudioRequest;
   import com.ankamagames.xgaming.audio.track.IAudioTrack;
   import com.ankamagames.xgaming.audio.track.TracksCollection;
   
   public class ConcurrentTracksManager extends AbstractTracksController
   {
      
      private var _tracks:IArrayList;
      
      public function ConcurrentTracksManager(param1:TracksCollection, param2:String)
      {
         super(param1,param2);
         this.init(param1);
      }
      
      override public function playSound(param1:AudioRequest) : void
      {
         if(!param1)
         {
            throw new ArgumentError("Request can\'t be null");
         }
         var _loc2_:IAudioTrack = this.getBestTrackToStartNewSound();
         _loc2_.setVolumes(ownVolumeToTransmit(),param1.volume);
         _loc2_.pan = param1.pan;
         _loc2_.load(param1.url);
         _loc2_.play(param1.loops);
      }
      
      override public function stopAllSounds() : void
      {
         var _loc1_:IIterator = this._tracks.getIterator();
         while(_loc1_.hasNext())
         {
            TrackAndTime(_loc1_.getNext()).track.stop();
         }
      }
      
      override protected function applyOwnVolumeToTracks() : void
      {
         var _loc1_:IIterator = this._tracks.getIterator();
         while(_loc1_.hasNext())
         {
            TrackAndTime(_loc1_.getNext()).track.setVolumes(ownVolumeToTransmit());
         }
      }
      
      private function init(param1:TracksCollection) : void
      {
         this._tracks = new ArrayList();
         var _loc2_:IIterator = param1.getIterator();
         while(_loc2_.hasNext())
         {
            this._tracks.addItem(new TrackAndTime(IAudioTrack(_loc2_.getNext()),0));
         }
      }
      
      private function getBestTrackToStartNewSound() : IAudioTrack
      {
         var _loc1_:IAudioTrack = null;
         var _loc2_:TrackAndTime = null;
         var _loc3_:IAudioTrack = null;
         var _loc4_:IIterator = this._tracks.getIterator();
         while(_loc4_.hasNext())
         {
            _loc2_ = _loc4_.getNext();
            _loc1_ = _loc2_.track;
            if(!_loc1_.isPlaying)
            {
               _loc3_ = _loc1_;
               break;
            }
         }
         if(_loc3_ == null)
         {
            this._tracks.sort(new TrackAndTimeComparator());
            _loc2_ = this._tracks.getFirstItem();
            _loc3_ = _loc2_.track;
         }
         _loc2_.playStartTime = lastUpdateTime;
         return _loc3_;
      }
   }
}

import as3.collections.IComparator;
import com.ankamagames.xgaming.audio.track.IAudioTrack;

class TrackAndTime
{
   
   private var _playStartTime:Number;
   
   private var _track:IAudioTrack;
   
   public function TrackAndTime(param1:IAudioTrack, param2:Number)
   {
      super();
      this._track = param1;
      this._playStartTime = param2;
   }
   
   public function get playStartTime() : Number
   {
      return this._playStartTime;
   }
   
   public function set playStartTime(param1:Number) : void
   {
      this._playStartTime = param1;
   }
   
   public function get track() : IAudioTrack
   {
      return this._track;
   }
   
   public function set track(param1:IAudioTrack) : void
   {
      this._track = param1;
   }
}

class TrackAndTimeComparator implements IComparator
{
   
   public function TrackAndTimeComparator()
   {
      super();
   }
   
   public function compare(param1:*, param2:*) : int
   {
      var _loc3_:TrackAndTime = param1 as TrackAndTime;
      var _loc4_:TrackAndTime = param2 as TrackAndTime;
      if(_loc3_.playStartTime < _loc4_.playStartTime)
      {
         return -1;
      }
      if(_loc3_.playStartTime > _loc4_.playStartTime)
      {
         return 1;
      }
      return 0;
   }
}
