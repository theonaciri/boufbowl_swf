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

      public function FrameController(startTime:int, duration:int = -1, useRealTime:Boolean = false, skipFrames:Boolean = true)
      {
         super();
         this._startTime = startTime;
         this._duration = duration;
         this._useRealTime = useRealTime;
         this._skipFrame = skipFrames;
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

      public function update(gameTime:int, realTime:int) : void
      {
         var nextFrame:int = 0;
         var loopElapsedFrames:Number = NaN;
         var time:int = this._useRealTime ? realTime : gameTime;
         if(this._lastFrameReached || this._totalFrames == -1 || time < this._startTime)
         {
            return;
         }
         var elapsedFrames:Number = (time - this._startTime) * Constants.DEFAULT_FRAME_PER_MILLISECONDS;
         if(elapsedFrames > this._movieEndFrame)
         {
            this._lastFrameReached = true;
            if(hasEventListener(LAST_FRAME_REACHED)) dispatchEvent(new Event(LAST_FRAME_REACHED));
            return;
         }
         if(this._loopBeginFrame == -1 || elapsedFrames < this._loopBeginFrame)
         {
            nextFrame = Math.ceil(elapsedFrames);
         }
         else if(elapsedFrames < this._loopsFinalEndFrame)
         {
            loopElapsedFrames = elapsedFrames - this._loopBeginFrame;
            nextFrame = this._loopBeginFrame + Math.ceil(loopElapsedFrames % this._loopFramesCount);
         }
         else
         {
            nextFrame = this._loopEndFrame + Math.ceil(elapsedFrames - this._loopsFinalEndFrame);
         }
         if(this._currentFrame != nextFrame)
         {
            if(!this._skipFrame && nextFrame > this._currentFrame)
            {
               ++this._currentFrame;
            }
            else
            {
               this._currentFrame = nextFrame;
            }
            if(hasEventListener(FRAME_CHANGED)) dispatchEvent(new Event(FRAME_CHANGED));
         }
      }

      public function setLoop(beginFrame:int, endFrame:int) : void
      {
         if(this._duration == -1)
         {
            return;
         }
         if(this._totalFrames == -1)
         {
            throw IllegalOperationError("totalFrames must be set prior to setLoop call");
         }
         if(beginFrame >= endFrame)
         {
            throw ArgumentError("beginFrame must be less than endFrame (beginFrame = " + beginFrame + ", endFrame = " + endFrame);
         }
         this._loopBeginFrame = beginFrame;
         this._loopEndFrame = endFrame;
         this._loopFramesCount = endFrame - beginFrame;
         var requestedLoopFrames:Number = this._duration * Constants.DEFAULT_FRAME_PER_MILLISECONDS - beginFrame - (this._totalFrames - endFrame);
         var loopedFrames:Number = this._loopFramesCount * Math.ceil(requestedLoopFrames / this._loopFramesCount);
         this._loopsFinalEndFrame = beginFrame + loopedFrames;
         this._movieEndFrame = beginFrame + loopedFrames + (this._totalFrames - endFrame);
      }
   }
}
