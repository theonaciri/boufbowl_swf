package com.ankamagames.boufbowl.resolution.display.script
{
   import as3.collections.IMap;
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.audio.ScriptSounds;
   import com.ankamagames.boufbowl.protocol.BoufbowlerStatus;
   import com.ankamagames.boufbowl.protocol.FightTest;
   import com.ankamagames.boufbowl.protocol.InteractionRole;
   import com.ankamagames.boufbowl.protocol.RegularOrderData.Element;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;
   import com.ankamagames.boufbowl.resolution.display.model.FxSlots;
   import com.ankamagames.boufbowl.resolution.display.model.FxSprites;
   import com.ankamagames.boufbowl.resolution.display.script.builder.PlaySoundActionBuilder;
   import com.ankamagames.boufbowl.resolution.display.script.builder.ScriptContext;
   import com.ankamagames.boufbowl.resolution.display.script.runner.AnimationEventKey;
   import com.ankamagames.boufbowl.resolution.display.script.runner.BoufbowlerAnimKeys;
   import com.ankamagames.boufbowl.resolution.display.script.runner.IBoufbowlerReference;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.INode;
   import com.ankamagames.xgaming.utils.getClassName;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.ankamagames.xgaming.utils.math.angle.radiansToDegrees;
   import com.ankamagames.xgaming.utils.math.angle.rangedDegrees;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.ankamagames.xgaming.utils.math.geom.HexVector;
   import com.ankamagames.xgaming.utils.math.geom.Point2;
   import com.ankamagames.xgaming.utils.math.geom.hexaToOrtho;
   import com.ankamagames.xgaming.utils.random.Dice;
   import com.netease.protobuf.Int64;
   import com.reider.log4AS3.ILogger;
   import flash.errors.IllegalOperationError;

   public class CommonInteractionFunctions extends ScriptBase
   {

      private static const LOGGER:ILogger = LoggerFactory.getLogger(CommonInteractionFunctions);

      private var _distanceToBall:int = 0;

      private var _participants:IMap;

      public function CommonInteractionFunctions(param1:IMap)
      {
         super(new ScriptContext());
         this._participants = param1;
      }

      final public function set distanceToBall(param1:int) : void
      {
         this._distanceToBall = param1;
      }

      final public function getBoufbowler(param1:int) : IBoufbowlerReference
      {
         var _loc2_:ParticipantData = this._participants.getItem(param1);
         return new BoufbowlerProxy(this,_loc2_.boufbowlerId);
      }

      final public function getBoufbowlerReference(param1:Int64) : IBoufbowlerReference
      {
         return new BoufbowlerProxy(this,param1);
      }

      final public function getData(param1:int) : ParticipantData
      {
         var _loc2_:ParticipantData = this._participants.getItem(param1);
         if(_loc2_ == null)
         {
            throw new IllegalStateError("Unknown role " + param1 + " for this interaction ");
         }
         return _loc2_;
      }

      public function buildNodes() : void
      {
         throw new IllegalOperationError("nodes() should be overriden");
      }

      final public function getNode() : INode
      {
         this.buildNodes();
         buildCurrentActionBuilder();
         var _loc1_:INode = context.tree.generateNode();
         _loc1_.structuralNode = true;
         _loc1_.label = getClassName(this);
         return _loc1_;
      }

      protected function getWinner(param1:ParticipantData, param2:ParticipantData, param3:FightTest) : ParticipantData
      {
         var _loc4_:ParticipantData = param3.winner == InteractionRole.FIRST_FIGHTER ? param1 : param2;
         _loc4_.fightScore = param3.score[0];
         return _loc4_;
      }

      protected function getLoser(param1:ParticipantData, param2:ParticipantData, param3:FightTest) : ParticipantData
      {
         var _loc4_:ParticipantData = param3.winner == InteractionRole.FIRST_FIGHTER ? param2 : param1;
         _loc4_.fightScore = param3.score[1];
         return _loc4_;
      }

      final protected function defaultDirection(param1:int) : int
      {
         return param1 == Side.LEFT ? 0 : 180;
      }

      final protected function getDefaultStaticAnimation(param1:ParticipantData) : AnimationKey
      {
         if(param1.mainOrder == Element.AIR)
         {
            return BoufbowlerAnimKeys.STATIC_AIR;
         }
         if(param1.mainOrder == Element.WATER)
         {
            return BoufbowlerAnimKeys.STATIC_WATER;
         }
         if(param1.mainOrder == Element.FIRE)
         {
            return BoufbowlerAnimKeys.STATIC_FIRE;
         }
         return BoufbowlerAnimKeys.STATIC_EARTH;
      }

      final protected function gaugeFx(param1:int, param2:int) : String
      {
         var _loc3_:int = 0;
         var _loc4_:String = null;
         if(param1 < 25)
         {
            _loc3_ = 1;
         }
         else if(param1 < 50)
         {
            _loc3_ = 2;
         }
         else if(param1 < 75)
         {
            _loc3_ = 3;
         }
         else
         {
            _loc3_ = 4;
         }
         switch(param2)
         {
            case Element.AIR:
               _loc4_ = "FX_aura_air_" + _loc3_;
               break;
            case Element.WATER:
               _loc4_ = "FX_aura_eau_" + _loc3_;
               break;
            case Element.FIRE:
               _loc4_ = "FX_aura_feu_" + _loc3_;
               break;
            case Element.EARTH:
               _loc4_ = "FX_aura_terre_" + _loc3_;
         }
         return _loc4_;
      }

      final protected function simpleMovement(param1:ParticipantData, param2:IBoufbowlerReference, param3:Number) : void
      {
         var _loc4_:int = 0;
         if(param1.trajectoryLength == 0)
         {
            return;
         }
         param2.moveToPoint(param1.startPosition).duration(0);
         if(param1.trajectoryLength > 1)
         {
            _loc4_ = 2;
            while(_loc4_ <= param1.trajectoryLength)
            {
               then();
               param2.moveToPoint(param1.getNthCell(_loc4_)).duration(param3 / (param1.trajectoryLength - 1));
               _loc4_++;
            }
         }
         else
         {
            wait(param3);
         }
      }

      final protected function displayBonusMalusNode(param1:ParticipantData, param2:IBoufbowlerReference) : INode
      {
         var _loc3_:String = param1.bonusReceived > 0 ? FxSprites.BONUS : (param1.bonusReceived < 0 ? FxSprites.MALUS : FxSprites.EMPTY);
         return group(param2.playFx(_loc3_,FxSlots.FACE).duration(500));
      }

      final protected function cutSceneMovement(param1:ParticipantData, param2:IBoufbowlerReference) : INode
      {
         if(param1.trajectoryLength > 2)
         {
            return sequence(waitRealTime(ScriptConstants.FREEZE_CUTSCENE_DURATION + 200),param2.moveToPoint(param1.getNthCell(param1.trajectoryLength - 1)).duration(0));
         }
         return group();
      }

      final protected function postCutSceneMovement(param1:ParticipantData, param2:IBoufbowlerReference, param3:Number) : INode
      {
         if(param1.trajectoryLength > 1)
         {
            return group(param2.moveToPoint(param1.endPosition).duration(param3));
         }
         return group();
      }

      protected function playCutScenePublicSound(param1:int, param2:String, param3:Boolean) : INode
      {
         if(param3)
         {
            return sequence(waitRealTime(param1),this.playSound(AudioConfiguration.AMBIANT,param2));
         }
         return group();
      }

      final protected function gridInterm(param1:HexPoint, param2:HexPoint) : HexPoint
      {
         if(param1.getDistance(param2) >= 2)
         {
            return new HexPoint(Math.floor((param1.x + param2.x) / 2),Math.ceil((param1.y + param2.y) / 2));
         }
         return param1;
      }

      final protected function hexaAngle(param1:HexVector) : Number
      {
         var _loc2_:Point2 = hexaToOrtho(param1);
         return rangedDegrees(radiansToDegrees(Math.atan2(_loc2_.y,_loc2_.x)));
      }

      final protected function shakeCam(param1:Boolean) : INode
      {
         if(param1)
         {
            return sequence(moveSceneViewByFromCenter(0,10,100),moveSceneViewByFromCenter(0,-5,100),moveSceneViewByFromCenter(0,0,100));
         }
         return group();
      }

      final protected function passZoom(param1:ParticipantData, param2:ParticipantData) : Number
      {
         return Math.max(ScriptConstants.ZOOM_MIN,Math.min(ScriptConstants.ZOOM_MAX,65 - 2 * param1.startPosition.getDistance(param2.startPosition)));
      }

      final protected function fightZoom(param1:HexPoint) : Number
      {
         return Math.max(ScriptConstants.ZOOM_DEFAULT,Math.min(ScriptConstants.ZOOM_MAX,ScriptConstants.ZOOM_MAX - (ScriptConstants.ZOOM_MAX - ScriptConstants.ZOOM_DEFAULT) * (Math.abs(param1.y) - 4) / 6));
      }

      override protected function playSound(param1:String, param2:String) : PlaySoundActionBuilder
      {
         var _loc3_:PlaySoundActionBuilder = super.playSound(param1,param2);
         _loc3_.volume(this.getVolume());
         return _loc3_;
      }

      protected function importantActionDisplayNode(param1:Boolean, param2:int, param3:int, param4:IBoufbowlerReference, param5:IBoufbowlerReference, param6:String, param7:String, param8:String = null, param9:HexPoint = null) : INode
      {
         var _loc10_:int = param2 == Side.LEFT ? 210 : 330;
         var _loc11_:int = 50;
         var _loc12_:int = new Dice(4).rollDice();
         var _loc13_:String = _loc12_ == 1 ? ScriptSounds.FREEZE_01 : (_loc12_ == 2 ? ScriptSounds.FREEZE_02 : (_loc12_ == 3 ? ScriptSounds.FREEZE_03 : ScriptSounds.FREEZE_04));
         var _loc14_:INode = param8 == null ? group() : group(this.playSound(AudioConfiguration.FX,param8).volume(ScriptConstants.VOLUME_FX_FOCUSED));
         var _loc15_:INode = param9 == null ? group() : group(moveCameraToHex(param9).duration(ScriptConstants.FREEZE_CAMERA_ROTATION_DURATION - 100));
         if(param1)
         {
            return sequence(group(setVolume(AudioConfiguration.STEPS,0),this.playSound(AudioConfiguration.FX,_loc13_).volume(ScriptConstants.VOLUME_FX_FOCUSED),zoomCamera(param3).duration(ScriptConstants.FREEZE_CAMERA_ROTATION_DURATION),_loc15_,rotateCamera(_loc10_).duration(ScriptConstants.FREEZE_CAMERA_ROTATION_DURATION),sequence(waitRealTime(ScriptConstants.FREEZE_COLOR_DELAY),group(param4.playFx(param6,FxSlots.LEGS_FRONT).realTime().duration(ScriptConstants.FREEZE_FX_DURATION),param5.playFx(param7,FxSlots.LEGS_FRONT).realTime().duration(ScriptConstants.FREEZE_FX_DURATION),param4.addColorFX().realTime().duration(ScriptConstants.FREEZE_COLOR_DURATION),param5.addColorFX().realTime().duration(ScriptConstants.FREEZE_COLOR_DURATION))),sequence(waitRealTime(ScriptConstants.FREEZE_COLOR_DELAY + ScriptConstants.FREEZE_COLOR_DURATION - _loc11_),group(_loc14_,waitRealTime(_loc11_)),group(setVolume(AudioConfiguration.STEPS,1),zoomCamera(ScriptConstants.ZOOM_DEFAULT).duration(200)))));
         }
         return group();
      }

      protected function twoPlayerCutSceneDisplayNode(param1:IBoufbowlerReference, param2:IBoufbowlerReference, param3:ParticipantData, param4:ParticipantData, param5:String, param6:String, param7:String, param8:String, param9:int = 0, param10:String = "", param11:Boolean = false) : INode
      {
         var _loc15_:Boolean = false;
         var _loc18_:int = 0;
         var _loc12_:int = new Dice(4).rollDice();
         var _loc13_:String = _loc12_ == 1 ? ScriptSounds.FREEZE_01 : (_loc12_ == 2 ? ScriptSounds.FREEZE_02 : (_loc12_ == 3 ? ScriptSounds.FREEZE_03 : ScriptSounds.FREEZE_04));
         var _loc14_:int = 50;
         var _loc16_:HexVector = param3.startPosition.vectorTo(param4.startPosition);
         var _loc17_:Number = this.hexaAngle(_loc16_);
         if(_loc17_ >= 345 || _loc17_ < 45)
         {
            _loc18_ = 270;
            _loc15_ = false;
         }
         if(_loc17_ >= 45 && _loc17_ < 115)
         {
            _loc18_ = 330;
            _loc15_ = false;
         }
         if(_loc17_ >= 115 && _loc17_ < 165)
         {
            _loc18_ = 210;
            _loc15_ = true;
         }
         if(_loc17_ >= 165 && _loc17_ < 225)
         {
            _loc18_ = 270;
            _loc15_ = true;
         }
         if(_loc17_ >= 225 && _loc17_ < 285)
         {
            _loc18_ = 330;
            _loc15_ = true;
         }
         if(_loc17_ >= 285 && _loc17_ < 345)
         {
            _loc18_ = 210;
            _loc15_ = false;
         }
         return sequence(slow(0),group(setVolume(AudioConfiguration.STEPS,0),this.playSound(AudioConfiguration.FX,_loc13_).volume(ScriptConstants.VOLUME_FX_FOCUSED),zoomCamera(ScriptConstants.ZOOM_CUTSCENE_END).duration(ScriptConstants.FREEZE_CUTSCENE_DURATION),moveCameraToHex(this.gridInterm(param3.startPosition,param4.startPosition)).duration(ScriptConstants.FREEZE_CAMERA_ROTATION_DURATION - 100),rotateCamera(_loc18_).duration(ScriptConstants.FREEZE_CAMERA_ROTATION_DURATION),param1.playFx(param5,FxSlots.LEGS_FRONT).realTime().duration(ScriptConstants.FREEZE_FX_CUTSCENE_DURATION),param2.playFx(param6,FxSlots.LEGS_FRONT).realTime().duration(ScriptConstants.FREEZE_FX_CUTSCENE_DURATION),param1.addColorFX().realTime().duration(ScriptConstants.FREEZE_COLOR_CUTSCENE_DURATION),param2.addColorFX().realTime().duration(ScriptConstants.FREEZE_COLOR_CUTSCENE_DURATION),sequence(waitRealTime(ScriptConstants.FREEZE_COLOR_DELAY + ScriptConstants.FREEZE_COLOR_CUTSCENE_DURATION - _loc14_ - ScriptConstants.CUTSCENE_TRANSITION_DURATION)
         ,playMovie("passerelle"),group(this.playCutScenePublicSound(param9,param10,param11),this.playSound(AudioConfiguration.FX,param8).volume(ScriptConstants.VOLUME_FX_FOCUSED),playCutScene(param7,[param1,param2]).illustration().flip(_loc15_)),zoomCamera(ScriptConstants.ZOOM_DEFAULT).duration(0),slow(1),setVolume(AudioConfiguration.STEPS,1),cameraFollows().ball())));
      }

      protected function winnerReplaceNode() : INode
      {
         var _loc4_:HexPoint = null;
         var _loc5_:int = 0;
         var _loc1_:ParticipantData = this.getData(InteractionRoles.WINNER);
         var _loc2_:IBoufbowlerReference = this.getBoufbowler(InteractionRoles.WINNER);
         var _loc3_:ParticipantData = this.getData(InteractionRoles.LOSER);
         if(_loc1_.startPosition.equals(_loc1_.endPosition) && _loc3_.startPosition.getDistance(_loc1_.startPosition) == 2)
         {
            _loc4_ = this.gridInterm(_loc1_.startPosition,_loc3_.startPosition);
            _loc5_ = this.hexaAngle(_loc4_.vectorTo(_loc3_.startPosition));
            LOGGER.debug("winnerStartPosition : {}, winnerIntermPosition : {},  winnerDirection :{}",_loc1_.startPosition,_loc4_,_loc5_);
            return sequence(_loc2_.playAnimation(BoufbowlerAnimKeys.REPLACE).facing(_loc5_).on(AnimationEventKey.MOVE_BEGIN).run(_loc2_.moveToPoint(_loc1_.endPosition).duration(300)),_loc2_.playAnimation(this.getDefaultStaticAnimation(_loc1_)).facing(_loc5_));
         }
         return sequence();
      }

      protected function playLoserFx(param1:IBoufbowlerReference, param2:ParticipantData, param3:String, param4:String) : INode
      {
         var _loc5_:int = 0;
         if(param2.status == BoufbowlerStatus.KO || !param2.alive)
         {
            return group(param1.playFx(FxSprites.MISS,FxSlots.FACE).duration(600),param1.playFx(param4,FxSlots.LEGS_BACK));
         }
         if(param2.status == BoufbowlerStatus.STUN)
         {
            _loc5_ = param2.stunDuration - 800;
            return group(param1.playFx(FxSprites.MISS,FxSlots.FACE).duration(600),param1.playFx(param3,FxSlots.FACE).duration(_loc5_));
         }
         return group(param1.playFx(FxSprites.MISS,FxSlots.FACE).duration(600));
      }

      protected function setLoserStatusAnimation(param1:ParticipantData, param2:IBoufbowlerReference, param3:AnimationKey, param4:Number) : INode
      {
         var _loc5_:int = 0;
         if(param1.status == BoufbowlerStatus.KO || !param1.alive)
         {
            return group(param2.playAnimation(param3).facing(param4).toStatic(param3));
         }
         _loc5_ = param1.stunDuration - 1000;
         return group(param2.setDirection(param4),param2.setStatic(param3),sequence(wait(_loc5_),param2.setStatic(this.getDefaultStaticAnimation(param1))));
      }

      protected function ballDispersionNode(param1:ParticipantData, param2:IBoufbowlerReference, param3:HexPoint, param4:Number = 200) : INode
      {
         if(param1.hasBall && param3 != null)
         {
            return group(param2.throwBallAtPoint(param3).duration(param4));
         }
         return group();
      }

      protected function getHpFxByDelta(param1:int) : String
      {
         if(param1 >= 0)
         {
            return this.hpGainFx(param1);
         }
         return this.hpLossFx(param1 * -1);
      }

      protected function hpGainFx(param1:int) : String
      {
         if(param1 < 0 || param1 > 9)
         {
            return FxSprites.EMPTY;
         }
         return "FX_Small_Gain_" + param1;
      }

      protected function hpLossFx(param1:int) : String
      {
         if(param1 == 0 || param1 > 9)
         {
            return FxSprites.EMPTY;
         }
         return "FX_Small_Lose_" + param1;
      }

      protected function hpCriticalLossFx(param1:int) : String
      {
         if(param1 == 0 || param1 > 9)
         {
            return FxSprites.EMPTY;
         }
         return "FX_Big_Lose_" + param1;
      }

      private function getVolume() : Number
      {
         if(this._distanceToBall < 4)
         {
            return 1;
         }
         if(this._distanceToBall < 6)
         {
            return 0.85;
         }
         if(this._distanceToBall < 8)
         {
            return 0.7;
         }
         if(this._distanceToBall < 11)
         {
            return 0.4;
         }
         if(this._distanceToBall < 13)
         {
            return 0.15;
         }
         return 0;
      }
   }
}
