package com.ankamagames.tiphon.display
{
   import com.ankamagames.jerakine.logger.Log;
   import com.ankamagames.jerakine.logger.Logger;
   import com.ankamagames.jerakine.utils.display.EnterFrameDispatcher;
   import com.ankamagames.jerakine.utils.display.MovieClipUtils;
   import com.ankamagames.tiphon.types.ScriptedAnimation;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.utils.Dictionary;
   import flash.utils.getQualifiedClassName;
   
   public class FpsControler
   {
      
      private static var _controledClipsCount:uint;
      
      protected static const _log:Logger = com.ankamagames.jerakine.logger.Log.getLogger(getQualifiedClassName(FpsControler));
      
      private static var _controledClips:Dictionary = new Dictionary(true);
      
      private static var _clipList:Dictionary = new Dictionary(true);

      private static var _playbackRates:Dictionary = new Dictionary(true);

      // Applied within the existing clock, so global replay speed/pause still
      // controls every animation and scripted frame markers are preserved.
      public static function setPlaybackRate(clip:MovieClip, rate:Number) : void
      {
         if(clip == null) return;
         if(!isFinite(rate) || rate < 0 || rate > 1)
            throw new ArgumentError("Playback rate must be between zero and one");
         if(rate == 1) delete _playbackRates[clip];
         else _playbackRates[clip] = rate;
      }
      
      public function FpsControler()
      {
         super();
      }
      
      public static function get controledClipsCount() : uint
      {
         return _controledClipsCount;
      }
      
      public static function Init() : void
      {
      }
      
      public static function controlFps(param1:MovieClip, param2:uint, param3:Boolean = false) : MovieClip
      {
         controlSingleClip(param1,param2,param3);
         return param1;
      }
      
      public static function controlScriptedAnimationFps(param1:ScriptedAnimation, param2:uint, param3:Boolean = false) : ScriptedAnimation
      {
         controlSingleClip(param1,param2,param3,true);
         return param1;
      }
      
      public static function uncontrolFps(container:DisplayObjectContainer) : void
      {
         var child:DisplayObject = null;
         if(container != null) delete _playbackRates[container];
         if(!container || MovieClipUtils.isSingleFrame(container))
         {
            return;
         }
         var childCount:uint = uint(container.numChildren);
         var childIndex:uint = 0;
         while(childIndex < childCount)
         {
            child = container.getChildAt(childIndex);
            if(child is DisplayObjectContainer)
            {
               uncontrolFps(child as DisplayObjectContainer);
            }
            childIndex++;
         }
         if(container is MovieClip)
         {
            MovieClip(container).isControled = null;
            delete _clipList[container];
         }
         stopMovieClip(container);
         if(_controledClips[container])
         {
            EnterFrameDispatcher.removeEventListener(_controledClips[container]);
            delete _controledClips[container];
            --_controledClipsCount;
         }
      }
      
      private static function controlSingleClip(param1:MovieClip, param2:uint, param3:Boolean = false, param4:Boolean = false) : DisplayObjectContainer
      {
         var _loc5_:uint = 0;
         var _loc6_:uint = 0;
         var _loc7_:DisplayObject = null;
         if(!param3)
         {
            _loc5_ = uint(param1.numChildren);
            _loc6_ = 0;
            while(_loc6_ < _loc5_)
            {
               _loc7_ = param1.getChildAt(_loc6_);
               if(_loc7_ is MovieClip)
               {
                  controlSingleClip(MovieClip(_loc7_),param2);
               }
               _loc6_++;
            }
         }
         if(!param1 || MovieClipUtils.isSingleFrame(param1) || Boolean(_controledClips[param1]))
         {
            return null;
         }
         MovieClip(param1).gotoAndStop(MovieClip(param1).currentFrame > 0 ? MovieClip(param1).currentFrame : 1);
         _controledClips[param1] = getControlingMethod(param1,param4);
         ++_controledClipsCount;
         EnterFrameDispatcher.addEventListener(_controledClips[param1],"FpsControler" + param1.name,param2);
         _clipList[param1] = null;
         MovieClip(param1).isControled = true;
         return param1;
      }
      
      public static function nextFrame() : void
      {
         var _loc1_:Object = null;
         var _loc2_:MovieClip = null;
         for(_loc1_ in _clipList)
         {
            _loc2_ = _loc1_ as MovieClip;
            _loc2_.gotoAndStop((_loc2_.currentFrame + 1) % (_loc2_.totalFrames + 1));
         }
      }
      
      public static function stopMovieClip(param1:DisplayObjectContainer) : void
      {
         var _loc4_:DisplayObject = null;
         if(param1 is MovieClip)
         {
            MovieClip(param1).stop();
         }
         var _loc2_:int = -1;
         var _loc3_:int = param1.numChildren;
         while(++_loc2_ < _loc3_)
         {
            _loc4_ = param1.getChildAt(_loc2_);
            if(_loc4_ is DisplayObjectContainer)
            {
               stopMovieClip(_loc4_ as DisplayObjectContainer);
            }
         }
      }
      
      private static function getControlingMethod(clip:MovieClip, isScriptedAnimation:Boolean = false) : Function
      {
         var frameCredit:Number = 0;
         if(isScriptedAnimation)
         {
            return function(event:Event):Boolean
            {
               frameCredit += _playbackRates[clip] === undefined ? 1 : Number(_playbackRates[clip]);
               if(frameCredit < 1) return false;
               frameCredit -= 1;
               var nextFrame:int = clip.currentFrame % clip.totalFrames + 1;
               clip.gotoAndStop(nextFrame);
               return ScriptedAnimation(clip).spriteHandler.tiphonEventManager.hasUnskippableEvent(nextFrame);
            };
         }
         return function(event:Event):Boolean
         {
            frameCredit += _playbackRates[clip] === undefined ? 1 : Number(_playbackRates[clip]);
            if(frameCredit < 1) return false;
            frameCredit -= 1;
            clip.gotoAndStop(clip.currentFrame % clip.totalFrames + 1);
            return false;
         };
      }
   }
}

