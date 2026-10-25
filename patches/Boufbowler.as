package com.ankamagames.boufbowl.resolution.display.model
{
   import as3.collections.IList;
   import as3.collections.LinkedList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;
   import com.ankamagames.boufbowl.resolution.display.animation.IBoufbowlerSprite;
   import com.ankamagames.boufbowl.resolution.display.model.event.AnimationDoneEvent;
   import com.ankamagames.boufbowl.resolution.display.model.event.DestinationReachedEvent;
   import com.ankamagames.boufbowl.resolution.display.model.event.FxChangedEvent;
   import com.ankamagames.boufbowl.resolution.display.model.event.InvalidateViewEvent;
   import com.ankamagames.boufbowl.resolution.display.model.movement.ITrajectory;
   import com.ankamagames.boufbowl.resolution.display.model.movement.Physics;
   import com.ankamagames.boufbowl.resolution.display.model.movement.SegmentTrajectory;
   import com.ankamagames.boufbowl.resolution.display.model.movement.TrajectoryFactory;
   import com.ankamagames.boufbowl.resolution.display.script.runner.AnimationEvent;
   import com.ankamagames.boufbowl.resolution.display.script.runner.AnimationEventKey;
   import com.ankamagames.boufbowl.resolution.display.script.runner.AnimationRepeat;
   import com.ankamagames.boufbowl.resolution.display.script.runner.BoufbowlerAnimKeys;
   import com.ankamagames.xgaming.utils.event.PropertyChangedEvent;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.ankamagames.xgaming.utils.math.geom.Point3;
   import com.ankamagames.tiphon.display.FpsControler;
   import com.ankamagames.tiphon.display.TiphonSprite;
   import com.reider.log4AS3.ILogger;
   import flash.events.Event;
   import flash.events.EventDispatcher;
   import flash.filters.ColorMatrixFilter;
   
   public class Boufbowler extends EventDispatcher implements IBoufbowler
   {
      
      public static const BOUFBOWLER_RUN_SPEED:int = 4;
      
      private static const _movementLogger:ILogger = LoggerFactory.getStringLogger("movement");
      
      private static var _nextUid:uint = 0;
      
      private var _hasBall:Boolean;
      
      private var _animation:AnimationKey;
      
      private var _currentDefaultRunAnimation:AnimationKey;
      
      private var _currentDefaultAnimation:AnimationKey;
      
      private var _currentStaticAnimation:AnimationKey;
      
      private var _repeat:AnimationRepeat;
      
      private var _fxEnabled:Boolean;
      
      private var _fxs:IList;
      
      private var _glow:Boolean;
      
      private var _colorFilter:ColorMatrixFilter;
      
      private var _sprite:IBoufbowlerSprite;
      
      private var _position:Point3;
      
      private var _direction:Number;
      
      private var _forcedDirection:Number;
      
      private var _trajectory:ITrajectory;

      private var _runAnimationRate:Number = 1;
      
      private var _team:BoufbowlTeam;
      
      private var _uid:uint;
      
      public function Boufbowler(sprite:IBoufbowlerSprite, team:BoufbowlTeam)
      {
         super();
         // FFDec's field-initializer postfix increment reuses constructor
         // registers (including this). Keep allocation explicit after super.
         this._uid = _nextUid;
         _nextUid = _nextUid + 1;
         this._sprite = sprite;
         this._team = team;
         this.init();
      }
      
      public function get hasBall() : Boolean
      {
         return this._hasBall;
      }
      
      public function set hasBall(param1:Boolean) : void
      {
         if(this._hasBall == param1)
         {
            return;
         }
         this._hasBall = param1;
         dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.HAS_BALL));
      }
      
      public function get position() : Point3
      {
         return this._position;
      }
      
      public function set position(param1:Point3) : void
      {
         if(param1.equals(this._position))
         {
            return;
         }
         this._position = param1;
         dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.POSITION));
      }
      
      public function get direction() : Number
      {
         return this._direction;
      }
      
      public function set direction(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw new ArgumentError("value can\'t be null");
         }
         if(this.internalSetDirection(param1))
         {
            dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.DIRECTION));
         }
      }
      
      public function get animation() : AnimationKey
      {
         return this._animation;
      }
      
      public function get repeat() : AnimationRepeat
      {
         return this._repeat;
      }
      
      public function get forcedDirection() : Number
      {
         return this._forcedDirection;
      }
      
      public function set forcedDirection(param1:Number) : void
      {
         if(this._forcedDirection == param1)
         {
            return;
         }
         this._forcedDirection = param1;
         dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.FORCED_DIRECTION));
      }
      
      public function get fxEnabled() : Boolean
      {
         return this._fxEnabled;
      }
      
      public function get glow() : Boolean
      {
         return this._glow;
      }
      
      public function set glow(param1:Boolean) : void
      {
         if(this._glow == param1)
         {
            return;
         }
         this._glow = param1;
         dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.GLOW));
      }
      
      public function set colorFilter(param1:ColorMatrixFilter) : void
      {
         if(this._colorFilter == param1)
         {
            return;
         }
         this._colorFilter = param1;
         dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.COLOR));
      }
      
      public function get colorFilter() : ColorMatrixFilter
      {
         return this._colorFilter;
      }
      
      public function get sprite() : IBoufbowlerSprite
      {
         return this._sprite;
      }
      
      public function get team() : BoufbowlTeam
      {
         return this._team;
      }
      
      public function set defaultRunAnimation(param1:AnimationKey) : void
      {
         this._currentDefaultRunAnimation = param1;
      }
      
      public function show() : void
      {
         dispatchEvent(new InvalidateViewEvent(InvalidateViewEvent.REDISPLAY_SPRITE));
      }
      
      public function hide() : void
      {
         dispatchEvent(new InvalidateViewEvent(InvalidateViewEvent.HIDE_SPRITE));
      }
      
      public function setClassSkin(param1:int) : void
      {
         this._sprite.boufbowlerClass = param1;
      }
      
      public function setAnimation(param1:AnimationKey, param2:AnimationRepeat) : void
      {
         if(param1 == null)
         {
            throw new ArgumentError("animation can\'t be null");
         }
         if(param2 == null)
         {
            throw new ArgumentError("repeat can\'t be null");
         }
         if(this.internalSetAnimation(param1,param2))
         {
            dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.ANIMATION));
         }
      }
      
      public function setDirection(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw new ArgumentError("direction can\'t be NaN");
         }
         if(this.internalSetDirection(param1))
         {
            dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.DIRECTION));
         }
      }
      
      public function setAnimationAndDirection(param1:AnimationKey, param2:AnimationRepeat, param3:Number) : void
      {
         if(param1 == null)
         {
            throw new ArgumentError("animation can\'t be null");
         }
         if(param2 == null)
         {
            throw new ArgumentError("repeat can\'t be null");
         }
         if(isNaN(param3))
         {
            throw new ArgumentError("direction can\'t be NaN");
         }
         var _loc4_:Boolean = this.internalSetAnimation(param1,param2);
         var _loc5_:Boolean = this.internalSetDirection(param3);
         if(_loc4_ && _loc5_)
         {
            dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.ANIMATION_AND_DIRECTION));
         }
         else if(_loc4_)
         {
            dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.ANIMATION));
         }
         else if(_loc5_)
         {
            dispatchEvent(new PropertyChangedEvent(BoufbowlerProperties.DIRECTION));
         }
      }
      
      public function setStatic(param1:AnimationKey) : void
      {
         if(this._currentDefaultAnimation.equals(this._currentStaticAnimation))
         {
            this._currentDefaultAnimation = param1;
         }
         this._currentStaticAnimation = param1;
      }
      
      public function moveTo(gameTime:int, destination:Point3, velocity:int) : void
      {
         _movementLogger.info("{} : {} depuis {} -> {}",this,gameTime,this.position,destination);
         this.updatePosition(gameTime);
         if(this.position.equals(destination))
         {
            dispatchEvent(new DestinationReachedEvent());
            return;
         }
         var distance:Number = destination.subtract(this.position).length;
         var duration:int = Physics.VELOCITY_TIME_UNIT * int(Math.ceil(distance / velocity));
         this._trajectory = new TrajectoryFactory().createSegmentTrajectory(gameTime,this.position,destination,velocity);
         this.setRunAnimationRate(distance,duration);
         this._currentDefaultAnimation = this._currentDefaultRunAnimation;
         this.setAnimToDefault();
         this.updateDirection(gameTime);
         this.updateRunningAnimationRate();
      }
      
      public function moveToDuration(gameTime:int, destination:Point3, duration:int) : void
      {
         this.updatePosition(gameTime);
         if(this.position.equals(destination))
         {
            dispatchEvent(new DestinationReachedEvent());
            return;
         }
         if(duration <= 0)
         {
            this.position = destination;
            dispatchEvent(new DestinationReachedEvent());
            return;
         }
         this.setRunAnimationRate(destination.subtract(this.position).length,duration);
         this._trajectory = new SegmentTrajectory(this.position,destination,gameTime,gameTime + duration);
         this._currentDefaultAnimation = this._currentDefaultRunAnimation;
         this.setAnimToDefault();
         this.updateDirection(gameTime);
         this.updateRunningAnimationRate();
      }
      
      public function stop() : void
      {
         this.cancelMovement();
      }
      
      public function addFx(param1:Fx) : void
      {
         this._fxs.addItem(param1);
         dispatchEvent(FxChangedEvent.fxAdded(param1));
      }
      
      public function removeFx(param1:Fx) : void
      {
         this._fxs.removeItem(param1);
         dispatchEvent(FxChangedEvent.fxRemoved(param1));
      }
      
      public function removeAllFxs() : void
      {
         while(this._fxs.numItems > 0)
         {
            this.removeFx(this._fxs.getFirstItem());
         }
      }
      
      public function update(gameTime:int, realTime:int) : void
      {
         this.updateDirection(gameTime);
         this.updatePosition(gameTime);
         this.updateMovement(gameTime);
         this.updateRunningAnimationRate();
         this.updateFxs(gameTime,realTime);
      }

      private function setRunAnimationRate(distance:Number, duration:int) : void
      {
         // Match the retained movement factory's normal velocity, independently
         // of display FPS. Global replay speed is already applied by Tiphon.
         this._runAnimationRate = duration > 0 ?
            Math.min(1,distance * Physics.VELOCITY_TIME_UNIT / (duration * Physics.DEFAULT_VELOCITY)) : 1;
      }

      private function updateRunningAnimationRate() : void
      {
         var sprite:TiphonSprite = this._sprite.getAnimationProvider().currentAnimation as TiphonSprite;
         if(sprite == null || sprite.rawAnimation == null) return;
         var running:Boolean = this._animation.equals(BoufbowlerAnimKeys.COURSE_NORMALE) ||
            this._animation.equals(BoufbowlerAnimKeys.COURSE_EAU) ||
            this._animation.equals(BoufbowlerAnimKeys.COURSE_NO_CIRCLE);
         FpsControler.setPlaybackRate(sprite.rawAnimation,
            running && this._trajectory != null ? this._runAnimationRate : 1);
      }
      
      override public function toString() : String
      {
         return "[Boufbowler #" + this._uid + "]";
      }
      
      public function onAnimationReachesEndFrame(param1:Event) : void
      {
         if(this._repeat)
         {
            this._repeat.advance();
         }
         this.setAnimToDefault();
      }
      
      public function onAnimationEventKey(param1:AnimationEventKey) : void
      {
         dispatchEvent(new AnimationEvent(param1));
      }
      
      private function init() : void
      {
         this._animation = BoufbowlerAnimKeys.DEFAULT;
         this._currentDefaultAnimation = BoufbowlerAnimKeys.DEFAULT;
         this._currentStaticAnimation = BoufbowlerAnimKeys.BOUFBOWLER_STATIC;
         this._currentDefaultRunAnimation = BoufbowlerAnimKeys.BOUFBOWLER_RUN;
         this._fxEnabled = true;
         this._fxs = new LinkedList();
         this._position = new Point3(0,0,0);
         this._direction = 0;
         this._forcedDirection = NaN;
      }
      
      private function internalSetAnimation(param1:AnimationKey, param2:AnimationRepeat) : Boolean
      {
         dispatchEvent(new AnimationDoneEvent(this._animation));
         if(param2.done())
         {
            dispatchEvent(new AnimationDoneEvent(this.animation));
            return false;
         }
         if(param1.equals(this._animation) && (this._repeat == param2 || this._repeat != null && param2 != null && this._repeat.equals(param2)))
         {
            return false;
         }
         this._animation = param1;
         this._repeat = param2;
         return true;
      }
      
      private function internalSetDirection(param1:Number) : Boolean
      {
         if(this._direction == param1)
         {
            return false;
         }
         this._direction = param1;
         return true;
      }
      
      private function setAnimToDefault() : void
      {
         if(Boolean(this._repeat) && this._repeat.done())
         {
            dispatchEvent(new AnimationDoneEvent(this._animation));
         }
         if(!this._repeat || this._repeat.done() || this._repeat.equals(AnimationRepeat.DEFAULT))
         {
            this.setAnimation(this._currentDefaultAnimation,AnimationRepeat.DEFAULT);
         }
      }
      
      private function updatePosition(param1:int) : void
      {
         if(!this._trajectory)
         {
            return;
         }
         this.position = this._trajectory.getPosition(param1);
      }
      
      private function updateDirection(param1:int) : void
      {
         if(!this._trajectory)
         {
            return;
         }
         this.direction = this._trajectory.getDirection(param1);
      }
      
      private function updateMovement(param1:int) : void
      {
         if(!this._trajectory)
         {
            return;
         }
         if(this._trajectory.isComplete(param1))
         {
            this.cancelMovement();
         }
      }
      
      private function updateFxs(param1:int, param2:int) : void
      {
         var _loc5_:Fx = null;
         var _loc3_:IList = new LinkedList();
         var _loc4_:IIterator = this._fxs.getIterator();
         while(_loc4_.hasNext())
         {
            _loc5_ = _loc4_.getNext();
            _loc5_.update(param1,param2);
            if(_loc5_.frameController.lastFrameReached)
            {
               _loc3_.addItem(_loc5_);
            }
         }
         _loc4_ = _loc3_.getIterator();
         while(_loc4_.hasNext())
         {
            this.removeFx(_loc4_.getNext());
         }
      }
      
      private function selectAnimationByVelocity(param1:int) : void
      {
         if(param1 == 0)
         {
            this._currentDefaultAnimation = this._currentStaticAnimation;
            return;
         }
         if(param1 < BOUFBOWLER_RUN_SPEED)
         {
            this._currentDefaultAnimation = BoufbowlerAnimKeys.BOUFBOWLER_WALK;
            return;
         }
         this._currentDefaultAnimation = BoufbowlerAnimKeys.BOUFBOWLER_RUN;
      }
      
      private function cancelMovement() : void
      {
         this._trajectory = null;
         dispatchEvent(new DestinationReachedEvent());
         if(this._trajectory == null)
         {
            this.selectAnimationByVelocity(0);
            this.setAnimToDefault();
         }
      }
   }
}

