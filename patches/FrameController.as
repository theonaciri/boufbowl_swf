package com.ankamagames.boufbowl.utils
{
   import com.ankamagames.boufbowl.resolution.display.Constants;
   import com.ankamagames.boufbowl.resolution.display.model.IUpdatable;
   import flash.errors.IllegalOperationError;
   import flash.events.Event;
   import flash.events.EventDispatcher;

   public class FrameController extends EventDispatcher implements IUpdatable
   {

      public static const LAST_FRAME_REACHED:String = "com.ankamagames.boufbowl.utils.FrameController.LAST_FRAME_REACHED";

      public static const FRAME_CHANGED:String = "com.ankamagames.boufbowl.utils.FrameController.FRAME_CHANGED";

      private var _startTime:int;

      private var _duration:int;

      private var _useRealTime:Boolean;

      private var _skipFrame:Boolean;

      private var _currentFrame:int = -1;

      private var _totalFrames:int = -1;

      private var _movieEndFrame:int = -1;

      private var _loopEndFrame:int = -1;

      private var _loopBeginFrame:int = -1;

      private var _loopFramesCount:int = -1;

      private var _loopsFinalEndFrame:int = -1;

      private var _lastFrameReached:Boolean = false;

      public function FrameController(param1:int, param2:int = -1, param3:Boolean = false, param4:Boolean = true)
      {
         super();
         this._startTime = param1;
         this._duration = param2;
         this._useRealTime = param3;
         this._skipFrame = param4;
      }

      public function get currentFrame() : int
      {
         return this._currentFrame;
      }

      public function set totalFrames(param1:int) : void
      {
         this._totalFrames = param1;
         this._movieEndFrame = param1;
      }

      public function get lastFrameReached() : Boolean
      {
         return this._lastFrameReached;
      }

      public function update(param1:int, param2:int) : void
      {
         var _loc5_:int = 0;
         var _loc6_:Number = NaN;
         var _loc3_:int = this._useRealTime ? param2 : param1;
         if(this._lastFrameReached || this._totalFrames == -1 || _loc3_ < this._startTime)
         {
            return;
         }
         var _loc4_:Number = (_loc3_ - this._startTime) * Constants.DEFAULT_FRAME_PER_MILLISECONDS;
         if(_loc4_ > this._movieEndFrame)
         {
            this._lastFrameReached = true;
            if(hasEventListener(LAST_FRAME_REACHED)) dispatchEvent(new Event(LAST_FRAME_REACHED));
            return;
         }
         if(this._loopBeginFrame == -1 || _loc4_ < this._loopBeginFrame)
         {
            _loc5_ = Math.ceil(_loc4_);
         }
         else if(_loc4_ < this._loopsFinalEndFrame)
         {
            _loc6_ = _loc4_ - this._loopBeginFrame;
            _loc5_ = this._loopBeginFrame + Math.ceil(_loc6_ % this._loopFramesCount);
         }
         else
         {
            _loc5_ = this._loopEndFrame + Math.ceil(_loc4_ - this._loopsFinalEndFrame);
         }
         if(this._currentFrame != _loc5_)
         {
            if(!this._skipFrame && _loc5_ > this._currentFrame)
            {
               ++this._currentFrame;
            }
            else
            {
               this._currentFrame = _loc5_;
            }
            if(hasEventListener(FRAME_CHANGED)) dispatchEvent(new Event(FRAME_CHANGED));
         }
      }

      public function setLoop(param1:int, param2:int) : void
      {
         if(this._duration == -1)
         {
            return;
         }
         if(this._totalFrames == -1)
         {
            throw IllegalOperationError("totalFrames must be set prior to setLoop call");
         }
         if(param1 >= param2)
         {
            throw ArgumentError("beginFrame must be less than endFrame (beginFrame = " + param1 + ", endFrame = " + param2);
         }
         this._loopBeginFrame = param1;
         this._loopEndFrame = param2;
         this._loopFramesCount = param2 - param1;
         var _loc3_:Number = this._duration * Constants.DEFAULT_FRAME_PER_MILLISECONDS - param1 - (this._totalFrames - param2);
         var _loc4_:Number = this._loopFramesCount * Math.ceil(_loc3_ / this._loopFramesCount);
         this._loopsFinalEndFrame = param1 + _loc4_;
         this._movieEndFrame = param1 + _loc4_ + (this._totalFrames - param2);
      }
   }
}
