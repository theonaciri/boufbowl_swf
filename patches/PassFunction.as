package com.ankamagames.boufbowl.client.match.resolution.interactions
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.audio.ScriptSounds;
   import com.ankamagames.boufbowl.protocol.InteractionOutcomeType;
   import com.ankamagames.boufbowl.protocol.ManeuverTest;
   import com.ankamagames.boufbowl.protocol.RegularOrderData.Element;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;
   import com.ankamagames.boufbowl.resolution.display.model.FxSlots;
   import com.ankamagames.boufbowl.resolution.display.model.FxSprites;
   import com.ankamagames.boufbowl.resolution.display.model.movement.Physics;
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
   import com.ankamagames.xgaming.utils.random.Dice;
   import com.reider.log4AS3.ILogger;

   public class PassFunction extends CommonInteractionFunctions
   {

      private static const LOGGER:ILogger = LoggerFactory.getLogger(PassFunction);

      private var _throwerStrength:Number;

      private var _receiverStrenght:Number;

      private var _cutScene:Boolean;

      private const passInteractionDuration:int = ScriptConstants.PASS_INTERACTION_DURATION;

      private var _receptionStatus:int;

      private var _passTrajectoryDuration:Number;

      private var _shortPassTrajectoryDuration:Number;

      private var _ballDestination:HexPoint;

      private var _ballTarget:HexPoint;

      private var _success:Boolean;

      private var _outcome:int;

      private var _cameraPosition:HexPoint;

      private var _zoom:Number;

      private const _fxDuration:int = 500;

      private const _freezeDuration:Number = 2700;

      private const _totalFxDuration:int = 3200;

      private var _fxDisabled:Boolean = false;

      private var _fxPass:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.THROWBALL;

      private var _fxRatage:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.MISS;

      private var _fxStun:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.STUN;

      public function PassFunction(param1:ParticipantData, param2:ParticipantData, param3:HexPoint, param4:HexPoint, param5:int, param6:Number, param7:ManeuverTest, param8:Number = 0, param9:Boolean = false)
      {
         LOGGER.debug("throwerPosition : {}, receiverPosition : {}, ballDestination = {}, ballTarget = {}",param1.startPosition,param2.startPosition,param3,param4);
         LOGGER.debug("passDuration : {}",param6);
         this._ballDestination = param3;
         this._ballTarget = param4;
         this._receptionStatus = param5;
         this._success = param7.success;
         this._outcome = param7.outcome;
         this._passTrajectoryDuration = this._receptionStatus == ScriptConstants.IS_RECEIVED || this._receptionStatus == ScriptConstants.FAILED_RECEPTION ? param6 - ScriptConstants.PASS_BALL_DELAY + ScriptConstants.RECEIVE_BALL_DELAY + ScriptConstants.PASS_OFFSET_DELAY : param6 - ScriptConstants.PASS_BALL_DELAY;
         this._shortPassTrajectoryDuration = param6 - ScriptConstants.PASS_BALL_DELAY + ScriptConstants.RECEIVE_SHORT_BALL_DELAY + ScriptConstants.PASS_OFFSET_DELAY;
         this._zoom = passZoom(param1,param2);
         this._cutScene = param9;
         this._receiverStrenght = param8;
         this._throwerStrength = param7.score.inherentScore;
         this._cameraPosition = gridInterm(param1.startPosition,param2.startPosition);
         var _loc10_:IMap = new Map();
         _loc10_.addItem(InteractionRoles.THROWER,param1);
         _loc10_.addItem(InteractionRoles.RECEIVER,param2);
         super(_loc10_);
      }

      override public function buildNodes() : void
      {
         var _loc1_:ParticipantData = getData(InteractionRoles.THROWER);
         var _loc2_:int = _loc1_.startPosition.getDistance(this._ballTarget);
         if(this._success == false && this._outcome == InteractionOutcomeType.CRITICAL)
         {
            if(_loc2_ < ScriptConstants.SHORT_PASS_MAX_LENGTH)
            {
               this.criticalFailedShortPass();
            }
            else
            {
               this.criticalFailedLongPass();
            }
         }
         else
         {
            if(_loc2_ < ScriptConstants.SHORT_PASS_MAX_LENGTH)
            {
               if(this._cutScene)
               {
                  this.cutScenePass();
               }
               else
               {
                  this.shortPassNode();
               }
            }
            if(_loc2_ >= ScriptConstants.SHORT_PASS_MAX_LENGTH && _loc1_.trajectoryLength == 1)
            {
               if(this._cutScene)
               {
                  this.cutScenePass();
               }
               else
               {
                  this.longPassNodeMotionless();
               }
            }
            if(_loc2_ >= ScriptConstants.SHORT_PASS_MAX_LENGTH && _loc1_.trajectoryLength > 1)
            {
               if(this._cutScene)
               {
                  this.cutScenePass();
               }
               else
               {
                  this.longPassNodeRun();
               }
            }
         }
      }

      private function cutScenePass() : void
      {
         var _loc5_:int = 0;
         var _loc6_:Boolean = false;
         var _loc1_:IBoufbowlerReference = getBoufbowler(InteractionRoles.THROWER);
         var _loc2_:ParticipantData = getData(InteractionRoles.THROWER);
         var _loc3_:IBoufbowlerReference = getBoufbowler(InteractionRoles.RECEIVER);
         var _loc4_:ParticipantData = getData(InteractionRoles.RECEIVER);
         var _loc7_:HexVector = _loc2_.startPosition.vectorTo(this._ballDestination);
         if(hexaAngle(_loc7_) >= 345 || hexaAngle(_loc7_) < 45)
         {
            _loc5_ = 270;
            _loc6_ = false;
         }
         if(hexaAngle(_loc7_) >= 45 && hexaAngle(_loc7_) < 115)
         {
            _loc5_ = 330;
            _loc6_ = false;
         }
         if(hexaAngle(_loc7_) >= 115 && hexaAngle(_loc7_) < 165)
         {
            _loc5_ = 210;
            _loc6_ = true;
         }
         if(hexaAngle(_loc7_) >= 165 && hexaAngle(_loc7_) < 225)
         {
            _loc5_ = 270;
            _loc6_ = true;
         }
         if(hexaAngle(_loc7_) >= 225 && hexaAngle(_loc7_) < 285)
         {
            _loc5_ = 330;
            _loc6_ = true;
         }
         if(hexaAngle(_loc7_) >= 285 && hexaAngle(_loc7_) < 345)
         {
            _loc5_ = 210;
            _loc6_ = false;
         }
         var _loc8_:int = new Dice(4).rollDice();
         var _loc9_:String = _loc8_ == 1 ? ScriptSounds.FREEZE_01 : (_loc8_ == 2 ? ScriptSounds.FREEZE_02 : (_loc8_ == 3 ? ScriptSounds.FREEZE_03 : ScriptSounds.FREEZE_04));
         var _loc10_:int = 50;
         _loc1_.playAnimation(BoufbowlerAnimKeys.LANCER_CUTSINE).facing(hexaAngle(_loc7_)).on(AnimationEventKey.FREEZE).run(sequence(slow(0),group(setVolume(AudioConfiguration.STEPS,0),playSound(AudioConfiguration.FX,_loc9_).volume(ScriptConstants.VOLUME_FX_FOCUSED),zoomCamera(passZoom(_loc2_,_loc4_)).duration(ScriptConstants.FREEZE_CUTSCENE_DURATION),moveCameraToHex(gridInterm(_loc2_.startPosition,_loc4_.startPosition)).duration(ScriptConstants.FREEZE_CAMERA_ROTATION_DURATION - 100),rotateCamera(_loc5_).duration(ScriptConstants.FREEZE_CAMERA_ROTATION_DURATION),_loc1_.playFx(gaugeFx(this._throwerStrength,Element.AIR),FxSlots.LEGS_FRONT).realTime().duration(ScriptConstants.FREEZE_FX_CUTSCENE_DURATION),_loc3_.playFx(gaugeFx(_loc4_.getElementCount(Element.AIR) > 0 ? int(this._receiverStrenght) : 0,Element.AIR),FxSlots.LEGS_FRONT).realTime().duration(ScriptConstants.FREEZE_FX_CUTSCENE_DURATION),_loc1_.addColorFX().realTime().duration(ScriptConstants.FREEZE_COLOR_CUTSCENE_DURATION),_loc3_.addColorFX()
         .realTime().duration(ScriptConstants.FREEZE_COLOR_CUTSCENE_DURATION),sequence(waitRealTime(ScriptConstants.FREEZE_COLOR_DELAY + ScriptConstants.FREEZE_COLOR_CUTSCENE_DURATION - _loc10_ - ScriptConstants.CUTSCENE_TRANSITION_DURATION),playMovie("passerelle"),group(playSound(AudioConfiguration.FX,ScriptSounds.CUTSCENE_PASS).volume(ScriptConstants.VOLUME_FX_FOCUSED),playCutScene(CutSceneKeys.PASS,[_loc1_]).illustration().flip(_loc6_)),slow(1),group(_loc1_.throwBallAtPoint(this._ballDestination).duration(0),sequence(playMovie(CutSceneKeys.TRAJECTOIRE_BALLE).flip(!_loc6_).duration(this._passTrajectoryDuration + 1000),this.passSimpleFailNode()))))));
         then();
         _loc1_.moveToPoint(_loc2_.endPosition).duration(0);
      }

      private function criticalFailedLongPass() : void
      {
         var _loc7_:AnimationKey = null;
         var _loc8_:int = 0;
         var _loc9_:int = 0;
         var _loc10_:String = null;
         var _loc1_:ParticipantData = getData(InteractionRoles.THROWER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.THROWER);
         var _loc3_:ParticipantData = getData(InteractionRoles.RECEIVER);
         var _loc4_:IBoufbowlerReference = getBoufbowler(InteractionRoles.RECEIVER);
         var _loc5_:HexVector = _loc1_.startPosition.vectorTo(this._ballTarget);
         var _loc6_:int = rangedDegrees(hexaAngle(_loc5_) - _loc1_.enteringDirection);
         if(_loc6_ >= 60 && _loc6_ <= 120)
         {
            _loc7_ = BoufbowlerAnimKeys.LANCER_GAUCHE;
            _loc8_ = ScriptConstants.HEIGHT_THROWER_SIDE;
            _loc9_ = _loc1_.enteringDirection + 120;
            _loc10_ = ScriptSounds.PASS_SIDE_FUMBLE;
         }
         if(_loc6_ > 120 && _loc6_ < 240)
         {
            _loc7_ = BoufbowlerAnimKeys.LANCER_DERRIERE;
            _loc8_ = ScriptConstants.HEIGHT_THROWER_BACK;
            _loc9_ = _loc1_.enteringDirection + 180;
            _loc10_ = ScriptSounds.PASS_BACK_FUMBLE;
         }
         if(_loc6_ >= 240 && _loc6_ <= 300)
         {
            _loc7_ = BoufbowlerAnimKeys.LANCER_DROITE;
            _loc8_ = ScriptConstants.HEIGHT_THROWER_SIDE;
            _loc9_ = _loc1_.enteringDirection - 120;
            _loc10_ = ScriptSounds.PASS_SIDE_FUMBLE;
         }
         if(_loc6_ < 60 || _loc6_ > 300)
         {
            _loc7_ = BoufbowlerAnimKeys.LANCER_DEVANT;
            _loc9_ = _loc1_.enteringDirection;
            _loc8_ = ScriptConstants.HEIGHT_THROWER_FRONT;
            _loc10_ = ScriptSounds.PASS_FRONT_FUMBLE;
         }
         var _loc11_:int = this._receptionStatus == ScriptConstants.IS_RECEIVED || this._receptionStatus == ScriptConstants.FAILED_RECEPTION ? ScriptConstants.HEIGHT_RECEIVER : (this._receptionStatus == ScriptConstants.HITS_RECEIVER ? ScriptConstants.HEIGHT_RECEIVER_CRITICAL : 0);
         group(_loc2_.playFx(this._fxPass,FxSlots.LEFT_HAND).realTime().duration(this._totalFxDuration),_loc2_.playAnimation(_loc7_).on(AnimationEventKey.FREEZE).run(importantActionDisplayNode(true,_loc1_.side,this._zoom,_loc2_,_loc4_,gaugeFx(this._throwerStrength,Element.AIR),gaugeFx(_loc3_.getElementCount(Element.AIR) > 0 ? int(this._receiverStrenght) : 0,Element.AIR),_loc10_,this._cameraPosition)).on(AnimationEventKey.THROW_BALL).run(group(cameraFollows().ball().velocity(Physics.DEFAULT_CAMERA_VELOCITY - 20),_loc2_.throwBallAtPoint(this._ballDestination).duration(this._passTrajectoryDuration).startingHeight(_loc8_).arrivalHeight(_loc11_),_loc2_.playFx(this._fxRatage,FxSlots.FACE).duration(600),sequence(wait(250),group(displayBonusMalusNode(_loc1_,_loc2_),_loc2_.playAnimation(BoufbowlerAnimKeys.ETOURDI_BIS).facing(_loc9_).toStatic(BoufbowlerAnimKeys.ETOURDI_BIS),_loc2_.playFx(this._fxStun,FxSlots.FACE).duration(_loc1_.stunDuration - 520))))));
         sequence(wait(_loc1_.stunDuration),_loc2_.setStatic(getDefaultStaticAnimation(_loc1_)));
      }

      private function criticalFailedShortPass() : void
      {
         var _loc1_:ParticipantData = getData(InteractionRoles.THROWER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.THROWER);
         var _loc3_:HexVector = _loc1_.startPosition.vectorTo(this._ballTarget);
         var _loc4_:int = this._receptionStatus == ScriptConstants.IS_RECEIVED || this._receptionStatus == ScriptConstants.FAILED_RECEPTION ? ScriptConstants.HEIGHT_RECEIVER_SHORTPASS : (this._receptionStatus == ScriptConstants.HITS_RECEIVER ? ScriptConstants.HEIGHT_RECEIVER_CRITICAL : 0);
         sequence(wait(200),group(_loc2_.playFx(this._fxPass,FxSlots.LEFT_HAND).realTime().duration(this._fxDuration),sequence(_loc2_.playAnimation(BoufbowlerAnimKeys.LANCER_PROCHE_ARRIERE).facing(hexaAngle(_loc3_) + 180).on(AnimationEventKey.FREEZE).run(playSound(AudioConfiguration.FX,ScriptSounds.PASS_SHORT_FUMBLE).volume(ScriptConstants.VOLUME_FX_FOCUSED)).on(AnimationEventKey.THROW_BALL).run(group(_loc2_.throwBallAtPoint(this._ballDestination).duration(this._passTrajectoryDuration).startingHeight(ScriptConstants.HEIGHT_THROWER_BACK).arrivalHeight(_loc4_),_loc2_.playFx(this._fxRatage,FxSlots.FACE).duration(600))),group(displayBonusMalusNode(_loc1_,_loc2_),_loc2_.playAnimation(BoufbowlerAnimKeys.ETOURDI_BIS).facing(hexaAngle(_loc3_)).toStatic(BoufbowlerAnimKeys.ETOURDI_BIS),_loc2_.playFx(this._fxStun,FxSlots.FACE).duration(_loc1_.stunDuration + 400)))));
         sequence(wait(this.passInteractionDuration + _loc1_.stunDuration),_loc2_.setStatic(getDefaultStaticAnimation(_loc1_)));
      }

      private function passSimpleFailNode() : INode
      {
         var _loc1_:IBoufbowlerReference = getBoufbowler(InteractionRoles.THROWER);
         if(!this._success)
         {
            return group(_loc1_.playFx(this._fxRatage,FxSlots.FACE).duration(300));
         }
         return group();
      }

      private function shortPassNode() : void
      {
         var _loc1_:ParticipantData = getData(InteractionRoles.THROWER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.THROWER);
         var _loc3_:HexVector = _loc1_.startPosition.vectorTo(this._ballTarget);
         var _loc4_:String = this._ballDestination.getDistance(this._ballTarget) > 2 ? ScriptSounds.PASS_FRONT_FAIL : ScriptSounds.PASS_SHORT;
         var _loc5_:int = this._receptionStatus == ScriptConstants.IS_RECEIVED || this._receptionStatus == ScriptConstants.FAILED_RECEPTION ? ScriptConstants.HEIGHT_RECEIVER_SHORTPASS : (this._receptionStatus == ScriptConstants.HITS_RECEIVER ? ScriptConstants.HEIGHT_RECEIVER_CRITICAL : 0);
         sequence(wait(200),group(_loc2_.playFx(this._fxPass,FxSlots.LEFT_HAND).realTime().duration(this._fxDuration),sequence(_loc2_.playAnimation(BoufbowlerAnimKeys.LANCER_PROCHE_ARRIERE).facing(hexaAngle(_loc3_) + 180).on(AnimationEventKey.FREEZE).run(playSound(AudioConfiguration.FX,_loc4_).volume(ScriptConstants.VOLUME_FX_FOCUSED)).on(AnimationEventKey.THROW_BALL).run(group(displayBonusMalusNode(_loc1_,_loc2_),_loc2_.throwBallAtPoint(this._ballDestination).duration(this._shortPassTrajectoryDuration).startingHeight(ScriptConstants.HEIGHT_THROWER_BACK).arrivalHeight(_loc5_),this.passSimpleFailNode())),_loc2_.setDirection(hexaAngle(_loc3_)))));
         simpleMovement(_loc1_,_loc2_,this.passInteractionDuration);
      }

      private function longPassNodeRun() : void
      {
         var _loc8_:Number = NaN;
         var _loc9_:AnimationKey = null;
         var _loc10_:String = null;
         var _loc11_:int = 0;
         var _loc1_:ParticipantData = getData(InteractionRoles.THROWER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.THROWER);
         var _loc3_:ParticipantData = getData(InteractionRoles.RECEIVER);
         var _loc4_:IBoufbowlerReference = getBoufbowler(InteractionRoles.RECEIVER);
         var _loc5_:HexPoint = _loc1_.trajectoryLength > 1 ? _loc1_.getNthCell(2) : _loc1_.startPosition;
         var _loc6_:HexVector = _loc1_.startPosition.vectorTo(this._ballTarget);
         var _loc7_:HexVector = _loc1_.startPosition.vectorTo(_loc5_);
         if(_loc5_.equals(_loc1_.startPosition))
         {
            _loc8_ = 0;
         }
         else
         {
            _loc8_ = rangedDegrees(hexaAngle(_loc6_) - hexaAngle(_loc7_));
         }
         if(_loc8_ >= 50 && _loc8_ <= 130)
         {
            _loc9_ = BoufbowlerAnimKeys.LANCER_GAUCHE;
            _loc11_ = ScriptConstants.HEIGHT_THROWER_SIDE;
            _loc10_ = this._ballDestination.getDistance(this._ballTarget) > 2 ? ScriptSounds.PASS_FRONT_FAIL : ScriptSounds.PASS_LEFT;
         }
         if(_loc8_ > 130 && _loc8_ < 230)
         {
            _loc9_ = BoufbowlerAnimKeys.LANCER_DERRIERE;
            _loc11_ = ScriptConstants.HEIGHT_THROWER_BACK;
            _loc10_ = this._ballDestination.getDistance(this._ballTarget) > 2 ? ScriptSounds.PASS_FRONT_FAIL : ScriptSounds.PASS_BACK;
         }
         if(_loc8_ >= 230 && _loc8_ <= 310)
         {
            _loc9_ = BoufbowlerAnimKeys.LANCER_DROITE;
            _loc11_ = ScriptConstants.HEIGHT_THROWER_SIDE;
            _loc10_ = this._ballDestination.getDistance(this._ballTarget) > 2 ? ScriptSounds.PASS_FRONT_FAIL : ScriptSounds.PASS_RIGHT;
         }
         if(_loc8_ < 50 || _loc8_ > 310)
         {
            _loc9_ = BoufbowlerAnimKeys.LANCER_DEVANT;
            _loc11_ = ScriptConstants.HEIGHT_THROWER_FRONT;
            _loc10_ = this._ballDestination.getDistance(this._ballTarget) > 2 ? ScriptSounds.PASS_FRONT_FAIL : ScriptSounds.PASS_FRONT;
         }
         var _loc12_:int = this._receptionStatus == ScriptConstants.IS_RECEIVED || this._receptionStatus == ScriptConstants.FAILED_RECEPTION ? ScriptConstants.HEIGHT_RECEIVER : (this._receptionStatus == ScriptConstants.HITS_RECEIVER ? ScriptConstants.HEIGHT_RECEIVER_CRITICAL : 0);
         group(_loc2_.playFx(this._fxPass,FxSlots.LEFT_HAND).realTime().duration(this._totalFxDuration),_loc2_.playAnimation(_loc9_).on(AnimationEventKey.FREEZE).run(importantActionDisplayNode(true,_loc1_.side,this._zoom,_loc2_,_loc4_,gaugeFx(this._throwerStrength,Element.AIR),gaugeFx(_loc3_.getElementCount(Element.AIR) > 0 ? int(this._receiverStrenght) : 0,Element.AIR),_loc10_,this._cameraPosition)).on(AnimationEventKey.THROW_BALL).run(group(displayBonusMalusNode(_loc1_,_loc2_),cameraFollows().ball().velocity(Physics.DEFAULT_CAMERA_VELOCITY - 20),_loc2_.throwBallAtPoint(this._ballDestination).duration(this._passTrajectoryDuration).startingHeight(_loc11_).arrivalHeight(_loc12_),this.passSimpleFailNode())));
         simpleMovement(_loc1_,_loc2_,this.passInteractionDuration);
      }

      private function longPassNodeMotionless() : void
      {
         var _loc1_:ParticipantData = getData(InteractionRoles.THROWER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.THROWER);
         var _loc3_:ParticipantData = getData(InteractionRoles.RECEIVER);
         var _loc4_:IBoufbowlerReference = getBoufbowler(InteractionRoles.RECEIVER);
         var _loc5_:HexVector = _loc1_.startPosition.vectorTo(this._ballTarget);
         var _loc6_:int = this._receptionStatus == ScriptConstants.IS_RECEIVED || this._receptionStatus == ScriptConstants.FAILED_RECEPTION ? ScriptConstants.HEIGHT_RECEIVER : (this._receptionStatus == ScriptConstants.HITS_RECEIVER ? ScriptConstants.HEIGHT_RECEIVER_CRITICAL : 0);
         var _loc7_:String = this._ballDestination.getDistance(this._ballTarget) > 2 ? ScriptSounds.PASS_FRONT_FAIL : ScriptSounds.PASS_FRONT;
         group(_loc2_.playFx(this._fxPass,FxSlots.LEFT_HAND).realTime().duration(this._totalFxDuration),_loc2_.playAnimation(BoufbowlerAnimKeys.LANCER_DEVANT).facing(hexaAngle(_loc5_)).on(AnimationEventKey.FREEZE).run(importantActionDisplayNode(true,_loc1_.side,this._zoom,_loc2_,_loc4_,gaugeFx(this._throwerStrength,Element.AIR),gaugeFx(_loc3_.getElementCount(Element.AIR) > 0 ? int(this._receiverStrenght) : 0,Element.AIR),_loc7_,this._cameraPosition)).on(AnimationEventKey.THROW_BALL).run(group(displayBonusMalusNode(_loc1_,_loc2_),cameraFollows().ball().velocity(Physics.DEFAULT_CAMERA_VELOCITY - 20),_loc2_.throwBallAtPoint(this._ballDestination).duration(this._passTrajectoryDuration).startingHeight(ScriptConstants.HEIGHT_THROWER_FRONT).arrivalHeight(_loc6_),this.passSimpleFailNode())));
      }
   }
}
