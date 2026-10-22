package com.ankamagames.boufbowl.client.match.resolution.interactions
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.audio.ScriptSounds;
   import com.ankamagames.boufbowl.protocol.InteractionOutcomeType;
   import com.ankamagames.boufbowl.protocol.ManeuverTest;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;
   import com.ankamagames.boufbowl.resolution.display.model.FxSlots;
   import com.ankamagames.boufbowl.resolution.display.model.FxSprites;
   import com.ankamagames.boufbowl.resolution.display.script.CommonInteractionFunctions;
   import com.ankamagames.boufbowl.resolution.display.script.CutSceneKeys;
   import com.ankamagames.boufbowl.resolution.display.script.InteractionRoles;
   import com.ankamagames.boufbowl.resolution.display.script.ParticipantData;
   import com.ankamagames.boufbowl.resolution.display.script.ScriptConstants;
   import com.ankamagames.boufbowl.resolution.display.script.runner.AnimationEventKey;
   import com.ankamagames.boufbowl.resolution.display.script.runner.BoufbowlerAnimKeys;
   import com.ankamagames.boufbowl.resolution.display.script.runner.IBoufbowlerReference;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.INode;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.ankamagames.xgaming.utils.math.angle.rangedDegrees;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.ankamagames.xgaming.utils.math.geom.HexVector;
   import com.reider.log4AS3.ILogger;

   public class ReceptionFunction extends CommonInteractionFunctions
   {

      private static const LOGGER:ILogger = LoggerFactory.getLogger(ReceptionFunction);

      private var _stadiumHasPublic:Boolean;

      private var _cutScene:Boolean;

      private const receptionInteractionDuration:int = ScriptConstants.RECEPTION_INTERACTION_DURATION;

      private var _success:Boolean;

      private var _outcome:int;

      private var _passStartPosition:HexPoint;

      private var _shortPass:Boolean;

      private var _dispersionPoint:HexPoint;

      private var _dispersionDuration:Number;

      private var _fxDisabled:Boolean = false;

      private var _fxReception:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.THROWBALL;

      private var _fxFall:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.GROUND_HIT;

      private var _fxRatage:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.MISS;

      private var _fxHit:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.HIT;

      public function ReceptionFunction(param1:ParticipantData, param2:HexPoint, param3:ManeuverTest, param4:Number, param5:Boolean, param6:HexPoint = null, param7:Number = 0, param8:Boolean = false)
      {
         var _loc9_:IMap = new Map();
         _loc9_.addItem(InteractionRoles.RECEIVER,param1);
         super(_loc9_);
         LOGGER.debug("receiverPosition = {}",param1.startPosition);
         if(param6 == null)
         {
            LOGGER.debug("dispersion undefined");
         }
         else
         {
            LOGGER.debug("dispersion = {}",param6);
         }
         this._success = param3.success;
         this._outcome = param3.outcome;
         this._stadiumHasPublic = param5;
         this._passStartPosition = param2;
         this._shortPass = param4 < ScriptConstants.SHORT_PASS_MAX_LENGTH;
         this._dispersionPoint = param6;
         this._dispersionDuration = param7 + ScriptConstants.DISPERSION_DELAY;
         this._cutScene = param8;
      }

      override public function buildNodes() : void
      {
         var _loc1_:ParticipantData = getData(InteractionRoles.RECEIVER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.RECEIVER);
         // An ordinary failed attempt does not take possession or stop a flight.
         if(!this._success && this._outcome != InteractionOutcomeType.CRITICAL && this._dispersionPoint == null)
         {
            _loc2_.playFx(this._fxRatage,FxSlots.FACE).duration(600);
            simpleMovement(_loc1_,_loc2_,600);
            return;
         }
         if(this._cutScene)
         {
            if(!this._success && this._outcome !== InteractionOutcomeType.CRITICAL)
            {
               this.simpleReception(_loc1_,_loc2_);
            }
            else if(!this._success && this._outcome == InteractionOutcomeType.CRITICAL)
            {
               this.cutsceneCriticalFailedReception(_loc1_,_loc2_);
            }
            else
            {
               this.cutsceneReception(_loc1_,_loc2_);
            }
         }
         else if(!this._success && this._outcome == InteractionOutcomeType.CRITICAL)
         {
            this.simpleCriticalFailedReception(_loc1_,_loc2_);
         }
         else
         {
            this.simpleReception(_loc1_,_loc2_);
         }
      }

      private function simpleCriticalFailedReception(param1:ParticipantData, param2:IBoufbowlerReference) : void
      {
         var _loc5_:int = 0;
         var _loc6_:AnimationKey = null;
         var _loc7_:AnimationKey = null;
         var _loc3_:HexVector = this._passStartPosition.vectorTo(param1.startPosition);
         var _loc4_:int = rangedDegrees(param1.enteringDirection - hexaAngle(_loc3_));
         if(_loc4_ > 60 && _loc4_ < 150)
         {
            _loc5_ = param1.enteringDirection + 60;
         }
         else if(_loc4_ > 210 && _loc4_ < 300)
         {
            _loc5_ = param1.enteringDirection - 60;
         }
         else
         {
            _loc5_ = param1.enteringDirection;
         }
         if(_loc4_ > 60 && _loc4_ < 300)
         {
            _loc6_ = BoufbowlerAnimKeys.STATIC_KO_DOS;
            _loc7_ = BoufbowlerAnimKeys.HIT_FACE;
         }
         else
         {
            _loc6_ = BoufbowlerAnimKeys.STATIC_KO_FACE;
            _loc7_ = BoufbowlerAnimKeys.HIT_DOS;
         }
         param2.playAnimation(BoufbowlerAnimKeys.RECEPTION).facing(_loc5_).on(AnimationEventKey.FX).run(param2.playFx(this._fxReception,FxSlots.LEFT_HAND).duration(450)).on(AnimationEventKey.CATCH_BALL).run(param2.playFx(this._fxHit,FxSlots.CUSTOM),param2.playAnimation(_loc7_).toStatic(_loc6_).on(AnimationEventKey.THROW_BALL).run(sequence(param2.pickupBall(),group(displayBonusMalusNode(param1,param2),param2.throwBallAtPoint(this._dispersionPoint).duration(this._dispersionDuration).atAngle(70)))).on(AnimationEventKey.FX).run(param2.playFx(this._fxFall,FxSlots.LEGS_BACK)));
      }

      private function cutsceneCriticalFailedReception(param1:ParticipantData, param2:IBoufbowlerReference) : void
      {
         sequence(group(playSound(AudioConfiguration.FX,ScriptSounds.CUTSCENE_RECEPTION_FUMBLE).volume(ScriptConstants.VOLUME_FX_FOCUSED),wait(ScriptConstants.RECEIVE_BALL_DELAY)),slow(0),group(playCutScenePublicSound(0,ScriptSounds.CUTSCENE_PUBLIC_03,this._stadiumHasPublic),playCutScene(CutSceneKeys.RECEPTION_FUMBLE,[param2]).illustration().flip(this.cutSceneFlip(this._passStartPosition.vectorTo(param1.startPosition)))),group(slow(1),this.catchBall(param2),param2.playAnimation(BoufbowlerAnimKeys.HIT_FACE).toStatic(BoufbowlerAnimKeys.STATIC_KO_DOS),zoomCamera(ScriptConstants.ZOOM_DEFAULT).duration(0),setVolume(AudioConfiguration.STEPS,1),cameraFollows().ball()));
      }

      private function cutsceneReception(param1:ParticipantData, param2:IBoufbowlerReference) : void
      {
         sequence(group(playSound(AudioConfiguration.FX,ScriptSounds.CUTSCENE_RECEPTION).volume(ScriptConstants.VOLUME_FX_FOCUSED),wait(ScriptConstants.RECEIVE_BALL_DELAY)),slow(0),group(playCutScenePublicSound(0,ScriptSounds.CUTSCENE_PUBLIC_02,this._stadiumHasPublic),playCutScene(CutSceneKeys.RECEPTION_OK,[param2]).illustration().flip(this.cutSceneFlip(this._passStartPosition.vectorTo(param1.startPosition)))),group(slow(1),this.catchBall(param2),param2.playAnimation(BoufbowlerAnimKeys.RECEPTION_CUTSINE_END_RACCORD),zoomCamera(ScriptConstants.ZOOM_DEFAULT).duration(0),setVolume(AudioConfiguration.STEPS,1),cameraFollows().ball()));
         simpleMovement(param1,param2,this.receptionInteractionDuration);
      }

      private function simpleReception(param1:ParticipantData, param2:IBoufbowlerReference) : void
      {
         var _loc6_:int = 0;
         var _loc8_:int = 0;
         var _loc9_:AnimationKey = null;
         var _loc3_:HexVector = this._passStartPosition.vectorTo(param1.startPosition);
         var _loc4_:HexVector = param1.trajectoryLength == 1 ? new HexVector(0,0) : param1.startPosition.vectorTo(param1.getNthCell(2));
         var _loc5_:int = param1.trajectoryLength > 1 ? int(rangedDegrees(hexaAngle(_loc4_) - hexaAngle(_loc3_))) : 0;
         if(param1.trajectoryLength == 1)
         {
            _loc6_ = hexaAngle(_loc3_) + 180;
         }
         else if(param1.trajectoryLength > 1 && _loc5_ > 60 && _loc5_ < 150)
         {
            _loc6_ = hexaAngle(_loc4_) + 60;
         }
         else if(param1.trajectoryLength > 1 && _loc5_ > 210 && _loc5_ < 300)
         {
            _loc6_ = hexaAngle(_loc4_) - 60;
         }
         else
         {
            _loc6_ = hexaAngle(_loc4_);
         }
         var _loc7_:int = this._success ? 600 : 400;
         if(!this._shortPass)
         {
            param2.playAnimation(BoufbowlerAnimKeys.RECEPTION).facing(_loc6_).on(AnimationEventKey.CATCH_BALL).run(group(this.catchBall(param2),displayBonusMalusNode(param1,param2))).on(AnimationEventKey.FX).run(param2.playFx(this._fxReception,FxSlots.LEFT_HAND).duration(_loc7_));
            simpleMovement(param1,param2,this.receptionInteractionDuration);
            if(param1.trajectoryLength == 1)
            {
               sequence(wait(this.receptionInteractionDuration),this.forceBall(param2));
            }
            else
            {
               then();
               this.forceBall(param2);
            }
         }
         else if(param1.trajectoryLength == 1)
         {
            group(sequence(param2.setDirection(hexaAngle(param1.startPosition.vectorTo(this._passStartPosition))),wait(100),param2.playAnimation(BoufbowlerAnimKeys.RECEPTION_COURT_ARRET).on(AnimationEventKey.CATCH_BALL).run(group(this.catchBall(param2),displayBonusMalusNode(param1,param2))).on(AnimationEventKey.FX).run(param2.playFx(this._fxReception,FxSlots.LEFT_HAND).duration(_loc7_))),sequence(wait(this.receptionInteractionDuration),this.forceBall(param2)));
         }
         else
         {
            _loc8_ = _loc4_.det(param1.startPosition.vectorTo(this._passStartPosition));
            _loc9_ = _loc8_ < 0 ? BoufbowlerAnimKeys.RAMASSAGE_COURSE_D : BoufbowlerAnimKeys.RAMASSAGE_COURSE_G;
            sequence(wait(100),param2.playAnimation(_loc9_).on(AnimationEventKey.CATCH_BALL).run(group(this.catchBall(param2),displayBonusMalusNode(param1,param2))).on(AnimationEventKey.FX).run(param2.playFx(this._fxReception,FxSlots.LEFT_HAND).duration(_loc7_)));
            simpleMovement(param1,param2,this.receptionInteractionDuration);
            then();
            this.forceBall(param2);
         }
      }

      private function catchBall(param1:IBoufbowlerReference) : INode
      {
         if(this._success)
         {
            return group(param1.pickupBall());
         }
         if(this._dispersionPoint == null)
         {
            LOGGER.debug("ball dispersion is undefined");
            return group(param1.playFx(this._fxRatage,FxSlots.FACE).duration(600));
         }
         return group(param1.playFx(this._fxRatage,FxSlots.FACE).duration(600),param1.throwBallAtPoint(this._dispersionPoint).duration(this._dispersionDuration));
      }

      private function cutSceneFlip(param1:HexVector) : Boolean
      {
         var _loc2_:Boolean = false;
         if(hexaAngle(param1) >= 285 || hexaAngle(param1) < 115)
         {
            _loc2_ = false;
         }
         if(hexaAngle(param1) >= 115 && hexaAngle(param1) < 285)
         {
            _loc2_ = true;
         }
         return !_loc2_;
      }

      private function forceBall(param1:IBoufbowlerReference) : INode
      {
         if(this._success)
         {
            return group(param1.pickupBall());
         }
         return group();
      }
   }
}
