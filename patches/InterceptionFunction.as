package com.ankamagames.boufbowl.client.match.resolution.interactions
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.audio.ScriptSounds;
   import com.ankamagames.boufbowl.protocol.InteractionOutcomeType;
   import com.ankamagames.boufbowl.protocol.ManeuverTest;
   import com.ankamagames.boufbowl.protocol.Side;
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
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.ankamagames.xgaming.utils.math.angle.rangedDegrees;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.ankamagames.xgaming.utils.math.geom.HexVector;
   import com.reider.log4AS3.ILogger;

   public class InterceptionFunction extends CommonInteractionFunctions
   {

      private static const LOGGER:ILogger = LoggerFactory.getLogger(InterceptionFunction);

      private var _stadiumHasPublic:Boolean;

      private var _cutScene:Boolean;

      private const interceptionInteractionDuration:int = ScriptConstants.INTERCEPTION_INTERACTION_DURATION;

      private var _success:Boolean;

      private var _outcome:int;

      private var _passStartPosition:HexPoint;

      private var _fxDisabled:Boolean = false;

      private var _fxReception:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.INTERCEPT;

      private var _fxFall:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.GROUND_HIT;

      public function InterceptionFunction(param1:ParticipantData, param2:HexPoint, param3:ManeuverTest, param4:Boolean, param5:Boolean = false)
      {
         var _loc6_:IMap = new Map();
         _loc6_.addItem(InteractionRoles.RECEIVER,param1);
         super(_loc6_);
         this._success = param3.success;
         this._outcome = param3.outcome;
         this._passStartPosition = param2;
         this._stadiumHasPublic = param4;
         this._cutScene = param5;
         LOGGER.debug("intercepterPosition : {}",param1.startPosition);
      }

      override public function buildNodes() : void
      {
         var _loc1_:ParticipantData = getData(InteractionRoles.RECEIVER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.RECEIVER);
         if(this._cutScene && (this._success || this._outcome == InteractionOutcomeType.CRITICAL))
         {
            this.cutsceneInterception(_loc1_,_loc2_);
         }
         else
         {
            this.simpleInterception(_loc1_,_loc2_);
         }
      }

      private function simpleInterception(param1:ParticipantData, param2:IBoufbowlerReference) : void
      {
         var _loc6_:int = 0;
         var _loc3_:HexVector = this._passStartPosition.vectorTo(param1.startPosition);
         var _loc4_:HexVector = param1.startPosition.vectorTo(param1.endPosition);
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
         var _loc7_:int = param1.side == Side.LEFT ? 210 : 330;
         if(!this._success)
         {
            if(this._outcome == InteractionOutcomeType.CRITICAL)
            {
               param2.playAnimation(BoufbowlerAnimKeys.RECEPTION).facing(_loc6_).on(AnimationEventKey.FX).run(sequence(wait(100),param2.playAnimation(BoufbowlerAnimKeys.HIT_DOS).on(AnimationEventKey.FX).run(param2.playFx(this._fxFall,FxSlots.LEGS_BACK)),param2.playAnimation(BoufbowlerAnimKeys.STATIC_KO_FACE).toStatic(BoufbowlerAnimKeys.STATIC_KO_FACE)));
            }
            else
            {
               displayBonusMalusNode(param1,param2);
               simpleMovement(param1,param2,this.interceptionInteractionDuration);
            }
         }
         else
         {
            param2.playAnimation(BoufbowlerAnimKeys.RECEPTION).facing(_loc6_).on(AnimationEventKey.CATCH_BALL).run(group(displayBonusMalusNode(param1,param2),param2.pickupBall(),rotateCamera(_loc7_).duration(300))).on(AnimationEventKey.FX).run(param2.playFx(this._fxReception,FxSlots.LEFT_HAND).duration(600));
            simpleMovement(param1,param2,this.interceptionInteractionDuration);
         }
      }

      private function cutsceneInterception(param1:ParticipantData, param2:IBoufbowlerReference) : void
      {
         if(this._success)
         {
            sequence(group(playSound(AudioConfiguration.FX,ScriptSounds.CUTSCENE_RECEPTION).volume(ScriptConstants.VOLUME_FX_FOCUSED),wait(ScriptConstants.RECEIVE_BALL_DELAY)),slow(0),group(playCutScenePublicSound(0,ScriptSounds.CUTSCENE_PUBLIC_02,this._stadiumHasPublic),playCutScene(CutSceneKeys.INTERCEPTION_OK,[param2]).illustration().flip(this.cutSceneFlip(this._passStartPosition.vectorTo(param1.startPosition)))),group(slow(1),param2.pickupBall(),param2.playAnimation(BoufbowlerAnimKeys.RECEPTION_CUTSINE_END_RACCORD),zoomCamera(ScriptConstants.ZOOM_DEFAULT).duration(0),setVolume(AudioConfiguration.STEPS,1),cameraFollows().ball()));
            simpleMovement(param1,param2,this.interceptionInteractionDuration);
         }
         else
         {
            sequence(group(playSound(AudioConfiguration.FX,ScriptSounds.CUTSCENE_RECEPTION_FUMBLE).volume(ScriptConstants.VOLUME_FX_FOCUSED),wait(ScriptConstants.RECEIVE_BALL_DELAY)),slow(0),group(playCutScenePublicSound(0,ScriptSounds.CUTSCENE_PUBLIC_01,this._stadiumHasPublic),playCutScene(CutSceneKeys.RECEPTION_FUMBLE,[param2]).illustration().flip(this.cutSceneFlip(this._passStartPosition.vectorTo(param1.startPosition)))),group(slow(1),param2.playAnimation(BoufbowlerAnimKeys.HIT_FACE).toStatic(BoufbowlerAnimKeys.STATIC_KO_DOS),zoomCamera(ScriptConstants.ZOOM_DEFAULT).duration(0),setVolume(AudioConfiguration.STEPS,1),cameraFollows().ball()));
         }
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
   }
}
