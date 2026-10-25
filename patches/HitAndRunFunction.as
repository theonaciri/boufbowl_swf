package com.ankamagames.boufbowl.client.match.resolution.interactions
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.protocol.BoufbowlerStatus;
   import com.ankamagames.boufbowl.protocol.FightTest;
   import com.ankamagames.boufbowl.protocol.InteractionOutcomeType;
   import com.ankamagames.boufbowl.protocol.InteractionRole;
   import com.ankamagames.boufbowl.protocol.RegularOrderData.Element;
   import com.ankamagames.boufbowl.protocol.TestScore;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;
   import com.ankamagames.boufbowl.resolution.display.model.FxSlots;
   import com.ankamagames.boufbowl.resolution.display.model.FxSprites;
   import com.ankamagames.boufbowl.resolution.display.script.CommonInteractionFunctions;
   import com.ankamagames.boufbowl.resolution.display.script.InteractionRoles;
   import com.ankamagames.boufbowl.resolution.display.script.ParticipantData;
   import com.ankamagames.boufbowl.resolution.display.script.ScriptConstants;
   import com.ankamagames.boufbowl.resolution.display.script.runner.AnimationEventKey;
   import com.ankamagames.boufbowl.resolution.display.script.runner.BoufbowlerAnimKeys;
   import com.ankamagames.boufbowl.resolution.display.script.runner.IBoufbowlerReference;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.INode;
   import com.ankamagames.xgaming.utils.math.angle.rangedDegrees;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.ankamagames.xgaming.utils.math.geom.HexVector;
   import com.ankamagames.xgaming.utils.random.Dice;
   
   public class HitAndRunFunction extends CommonInteractionFunctions
   {
      
      private const hitAndRunDuration:Number = 1000;
      
      private const isFront:int = 1;
      
      private const isBack:int = 3;
      
      private const isLeft:int = 2;
      
      private const isRight:int = 4;
      
      private const isMotionless:int = 0;
      
      private var _zoomFactor:int;
      
      private var _ballDispersionPoint:HexPoint;
      
      private var _winnerStrength:Number;
      
      private var _loserStrength:Number;
      
      private var _outcome:int;
      
      private var _hitStunSound:String = "interactions/stun_run_01.mp3";
      
      private var _hitStun02Sound:String = "interactions/stun_run_02.mp3";
      
      private var _hitStun03Sound:String = "interactions/stun_run_03.mp3";
      
      private var _hitStunReplaceSound:String = "interactions/stun_strike_01.mp3";
      
      private var _hitStunShootSound:String = "interactions/stun_shoot_01.mp3";
      
      private var _hitKOBackSound:String = "interactions/ko_front_strike_01.mp3";
      
      private var _hitKOBackRunSound:String = "interactions/ko_front_run_01.mp3";
      
      private var _hitKOBackRun02Sound:String = "interactions/ko_front_run_02.mp3";
      
      private var _hitKOBackRun03Sound:String = "interactions/ko_front_run_03.mp3";
      
      private var _hitKOBackRun04Sound:String = "interactions/ko_front_run_04.mp3";
      
      private var _hitKOBackReplaceSound:String = "interactions/ko_front_strike_replace_01.mp3";
      
      private var _hitKOBackShootSound:String = "interactions/ko_front_shoot_01.mp3";
      
      private var _hitKOFrontSound:String = "interactions/ko_back_strike_02.mp3";
      
      private var _hitKOFrontRunSound:String = "interactions/ko_back_run_02.mp3";
      
      private var _hitKOFrontReplaceSound:String = "interactions/ko_back_strike_replace_01.mp3";
      
      private var _hitKOFrontShootSound:String = "interactions/ko_back_shoot_01.mp3";
      
      private var _fxDisabled:Boolean = false;
      
      private var _fxKO:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.GROUND_HIT;
      
      private var _fxStun:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.STUN;
      
      private var _fxTackle:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.TACKLE;
      
      private var _fxKick:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.HIT_N_RUN_BACK;
      
      private var _fxSwipe:String = this._fxDisabled ? FxSprites.EMPTY : FxSprites.HIT_N_RUN_FRONT;
      
      public function HitAndRunFunction(first:ParticipantData, second:ParticipantData, result:FightTest, dispersion:HexPoint = null)
      {
         var participants:IMap = new Map();
         participants.addItem(InteractionRoles.WINNER,getWinner(first,second,result));
         participants.addItem(InteractionRoles.LOSER,getLoser(first,second,result));
         super(participants);
         this._zoomFactor = fightZoom(gridInterm(first.startPosition,second.startPosition));
         this._ballDispersionPoint = dispersion;
         this._winnerStrength = result.score[result.winner == InteractionRole.FIRST_FIGHTER ? 0 : 1].inherentScore;
         this._loserStrength = result.score[result.winner == InteractionRole.FIRST_FIGHTER ? 1 : 0].inherentScore;
         this._outcome = result.outcome;
      }

      override public function buildNodes() : void
      {
         var _loc1_:ParticipantData = getData(InteractionRoles.WINNER);
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.WINNER);
         var _loc3_:ParticipantData = getData(InteractionRoles.LOSER);
         var _loc4_:IBoufbowlerReference = getBoufbowler(InteractionRoles.LOSER);
         var _loc5_:Boolean = _loc3_.hasBall || _loc1_.hasBall;
         if(this.relativePosition(_loc1_,_loc3_) == this.isMotionless)
         {
            this.hitAndRunMotionless(_loc1_,_loc2_,_loc3_,_loc4_,_loc5_);
         }
         if(this.relativePosition(_loc1_,_loc3_) == this.isFront)
         {
            this.hitAndRunFront(_loc1_,_loc2_,_loc3_,_loc4_,_loc5_);
         }
         if(this.relativePosition(_loc1_,_loc3_) == this.isBack)
         {
            this.hitAndRunBack(_loc1_,_loc2_,_loc3_,_loc4_,_loc5_);
         }
         if(this.relativePosition(_loc1_,_loc3_) == this.isLeft || this.relativePosition(_loc1_,_loc3_) == this.isRight)
         {
            this.hitAndRunSides(_loc1_,_loc2_,_loc3_,_loc4_,_loc5_);
         }
      }
      
      private function relativePosition(param1:ParticipantData, param2:ParticipantData) : int
      {
         var _loc6_:int = 0;
         var _loc3_:HexVector = param1.trajectoryLength > 1 ? param1.startPosition.vectorTo(param1.getNthCell(2)) : null;
         var _loc4_:HexVector = param1.startPosition.vectorTo(param2.startPosition);
         var _loc5_:Number = param1.trajectoryLength > 1 ? rangedDegrees(hexaAngle(_loc4_) - hexaAngle(_loc3_)) : 0;
         if(param1.trajectoryLength == 1)
         {
            _loc6_ = this.isMotionless;
         }
         if(param1.trajectoryLength > 1 && (_loc5_ < 60 || _loc5_ > 300))
         {
            _loc6_ = this.isFront;
         }
         if(param1.trajectoryLength > 1 && _loc5_ >= 60 && _loc5_ < 90)
         {
            _loc6_ = this.isLeft;
         }
         if(param1.trajectoryLength > 1 && _loc5_ >= 90 && _loc5_ <= 270)
         {
            _loc6_ = this.isBack;
         }
         if(param1.trajectoryLength > 1 && _loc5_ > 270 && _loc5_ <= 300)
         {
            _loc6_ = this.isRight;
         }
         return _loc6_;
      }
      
      private function loserHitNode(param1:ParticipantData, param2:IBoufbowlerReference, param3:ParticipantData, param4:IBoufbowlerReference) : INode
      {
         var _loc7_:int = 0;
         var _loc8_:AnimationKey = null;
         var _loc9_:AnimationKey = null;
         var _loc5_:Boolean = param3.status == BoufbowlerStatus.KO || !param3.alive;
         var _loc6_:int = hexaAngle(gridInterm(param1.startPosition,param3.startPosition).vectorTo(param3.startPosition));
         if(!_loc5_ || !param3.isDodging)
         {
            _loc7_ = hexaAngle(param3.startPosition.vectorTo(gridInterm(param1.startPosition,param3.startPosition)));
         }
         else
         {
            _loc7_ = param3.enteringDirection;
         }
         var _loc10_:int = new Dice(2).rollDice();
         var _loc11_:AnimationKey = _loc10_ == 1 ? BoufbowlerAnimKeys.ETOURDI : BoufbowlerAnimKeys.ETOURDI_BIS;
         if(!_loc5_)
         {
            _loc8_ = BoufbowlerAnimKeys.HIT_DEBOUT;
            _loc9_ = _loc11_;
         }
         else if(param3.isDodging && (rangedDegrees(_loc6_ - _loc7_) <= 90 || rangedDegrees(_loc6_ - _loc7_) >= 270))
         {
            _loc8_ = BoufbowlerAnimKeys.HIT_DOS;
            _loc9_ = BoufbowlerAnimKeys.STATIC_KO_FACE;
         }
         else
         {
            _loc8_ = BoufbowlerAnimKeys.HIT_FACE;
            _loc9_ = BoufbowlerAnimKeys.STATIC_KO_DOS;
         }
         var _loc12_:String = this._outcome == InteractionOutcomeType.CRITICAL ? hpCriticalLossFx(param3.damageTaken) : hpLossFx(param3.damageTaken);
         var _loc13_:Boolean = param3.hasBall || param1.hasBall;
         var _loc14_:Boolean = (_loc13_) && _loc5_;
         return group(param4.addOnomatopeia(_loc12_),displayBonusMalusNode(param1,param2),sequence(param4.playAnimation(_loc8_).facing(_loc7_).on(AnimationEventKey.THROW_BALL).run(ballDispersionNode(param3,param4,this._ballDispersionPoint)).on(AnimationEventKey.FX).run(group(playLoserFx(param4,param3,this._fxStun,this._fxKO),shakeCam(_loc14_))),setLoserStatusAnimation(param3,param4,_loc9_,_loc7_)));
      }
      
      private function loserHitSound(param1:ParticipantData, param2:ParticipantData) : String
      {
         var _loc5_:int = 0;
         var _loc7_:int = 0;
         var _loc8_:int = 0;
         var _loc3_:int = hexaAngle(gridInterm(param1.startPosition,param2.startPosition).vectorTo(param2.startPosition));
         var _loc4_:Boolean = param1.startPosition.equals(param1.endPosition) && param2.startPosition.getDistance(param1.startPosition) == 2;
         var _loc6_:Boolean = param2.status == BoufbowlerStatus.KO || !param2.alive;
         if(!_loc6_ || !param2.isDodging)
         {
            _loc5_ = hexaAngle(param2.startPosition.vectorTo(gridInterm(param1.startPosition,param2.startPosition)));
         }
         else
         {
            _loc5_ = param2.enteringDirection;
         }
         if(!_loc6_)
         {
            if(_loc4_)
            {
               return this._hitStunReplaceSound;
            }
            if(this.relativePosition(param1,param2) == this.isBack)
            {
               return this._hitStunShootSound;
            }
            _loc7_ = new Dice(3).rollDice();
            return _loc7_ == 1 ? this._hitStunSound : (_loc7_ == 2 ? this._hitStun02Sound : this._hitStun03Sound);
         }
         if(param2.isDodging && (rangedDegrees(_loc3_ - _loc5_) <= 90 || rangedDegrees(_loc3_ - _loc5_) >= 270))
         {
            if(_loc4_)
            {
               return this._hitKOFrontReplaceSound;
            }
            if(this.relativePosition(param1,param2) == this.isBack)
            {
               return this._hitKOFrontShootSound;
            }
            if(this.relativePosition(param1,param2) == this.isLeft || this.relativePosition(param1,param2) == this.isRight)
            {
               return this._hitKOFrontRunSound;
            }
            return this._hitKOFrontSound;
         }
         if(_loc4_)
         {
            return this._hitKOBackReplaceSound;
         }
         if(this.relativePosition(param1,param2) == this.isBack)
         {
            return this._hitKOBackShootSound;
         }
         if(this.relativePosition(param1,param2) == this.isLeft || this.relativePosition(param1,param2) == this.isRight)
         {
            _loc8_ = new Dice(4).rollDice();
            return _loc8_ == 1 ? this._hitKOBackRunSound : (_loc8_ == 2 ? this._hitKOBackRun02Sound : (_loc8_ == 3 ? this._hitKOBackRun03Sound : this._hitKOBackRun04Sound));
         }
         return this._hitKOBackSound;
      }
      
      private function loserAnimNode(param1:ParticipantData, param2:ParticipantData, param3:IBoufbowlerReference) : void
      {
         var _loc4_:HexPoint = gridInterm(param1.startPosition,param2.startPosition);
         var _loc5_:int = hexaAngle(param2.startPosition.vectorTo(_loc4_));
         if(param2.isDodging)
         {
            param3.playAnimation(BoufbowlerAnimKeys.ESQUIVE_FAIL);
         }
         else
         {
            param3.playAnimation(BoufbowlerAnimKeys.TAMPON_FACE).facing(_loc5_);
         }
      }
      
      private function hitAndRunBack(param1:ParticipantData, param2:IBoufbowlerReference, param3:ParticipantData, param4:IBoufbowlerReference, param5:Boolean) : void
      {
         var _loc6_:HexPoint = param3.isDodging ? param3.startPosition : gridInterm(param3.startPosition,param1.startPosition);
         var _loc7_:int = param3.status == BoufbowlerStatus.KO || !param3.alive ? 800 : 450;
         var _loc8_:String = param3.isDodging ? gaugeFx(this._loserStrength,Element.FIRE) : gaugeFx(this._loserStrength,Element.EARTH);
         var _loc9_:String = gaugeFx(this._winnerStrength,Element.EARTH);
         var _loc10_:int = param3.hasBall ? param3.side : param1.side;
         var _loc11_:Number = ScriptConstants.VOLUME_FX_FOCUSED;
         param4.moveToPoint(_loc6_);
         this.loserAnimNode(param1,param3,param4);
         param2.playAnimation(BoufbowlerAnimKeys.TAMPON_DOS).facing(hexaAngle(param1.startPosition.vectorTo(param3.startPosition)) + 180).on(AnimationEventKey.FX).run(param2.playFx(this._fxKick,FxSlots.CUSTOM)).on(AnimationEventKey.SOUND).run(playSound(AudioConfiguration.FX,this.loserHitSound(param1,param3)).volume(_loc11_)).on(AnimationEventKey.STRIKE).run(group(param4.moveToPoint(param3.startPosition).duration(_loc7_),this.loserHitNode(param1,param2,param3,param4))).on(AnimationEventKey.FREEZE).run(importantActionDisplayNode(param5,_loc10_,this._zoomFactor,param4,param2,_loc8_,_loc9_));
         simpleMovement(param1,param2,this.hitAndRunDuration);
      }
      
      private function hitAndRunFront(param1:ParticipantData, param2:IBoufbowlerReference, param3:ParticipantData, param4:IBoufbowlerReference, param5:Boolean) : void
      {
         var _loc12_:int = 0;
         var _loc6_:int = hexaAngle(param1.getNthCell(2).vectorTo(param3.startPosition));
         var _loc7_:String = param3.isDodging ? gaugeFx(this._loserStrength,Element.FIRE) : gaugeFx(this._loserStrength,Element.EARTH);
         var _loc8_:String = gaugeFx(this._winnerStrength,Element.EARTH);
         var _loc9_:int = param1.hasBall ? param1.side : param3.side;
         var _loc10_:int = 600;
         var _loc11_:Number = param5 ? ScriptConstants.VOLUME_FX_FOCUSED : ScriptConstants.VOLUME_FX_UNFOCUSED;
         this.loserAnimNode(param1,param3,param4);
         param2.playAnimation(BoufbowlerAnimKeys.TACLE_OK).facing(_loc6_).on(AnimationEventKey.FREEZE).run(importantActionDisplayNode(param5,_loc9_,this._zoomFactor,param2,param4,_loc8_,_loc7_)).on(AnimationEventKey.FX).run(param2.playFx(this._fxTackle,FxSlots.CUSTOM)).on(AnimationEventKey.SOUND).run(playSound(AudioConfiguration.FX,this.loserHitSound(param1,param3)).volume(_loc11_)).on(AnimationEventKey.STRIKE).run(group(param2.moveToPoint(param1.getNthCell(2)).duration(0),this.loserHitNode(param1,param2,param3,param4)));
         wait(_loc10_);
         if(param1.trajectoryLength > 2)
         {
            _loc12_ = 3;
            while(_loc12_ <= param1.trajectoryLength)
            {
               then();
               param2.moveToPoint(param1.getNthCell(_loc12_)).duration((this.hitAndRunDuration - _loc10_) / (param1.trajectoryLength - 2));
               _loc12_++;
            }
         }
      }
      
      private function hitAndRunSides(param1:ParticipantData, param2:IBoufbowlerReference, param3:ParticipantData, param4:IBoufbowlerReference, param5:Boolean) : void
      {
         var _loc6_:int = param1.hasBall ? param1.side : param3.side;
         var _loc7_:String = param3.isDodging ? gaugeFx(this._loserStrength,Element.FIRE) : gaugeFx(this._loserStrength,Element.EARTH);
         var _loc8_:String = gaugeFx(this._winnerStrength,Element.EARTH);
         var _loc9_:Number = param5 ? ScriptConstants.VOLUME_FX_FOCUSED : ScriptConstants.VOLUME_FX_UNFOCUSED;
         this.loserAnimNode(param1,param3,param4);
         param2.playAnimation(BoufbowlerAnimKeys.TAMPON_FACE).facing(hexaAngle(param1.startPosition.vectorTo(param3.startPosition))).on(AnimationEventKey.FREEZE).run(importantActionDisplayNode(param5,_loc6_,this._zoomFactor,param2,param4,_loc8_,_loc7_)).on(AnimationEventKey.FX).run(group(param2.playFx(this._fxSwipe,FxSlots.LEFT_HAND),param2.playFx(this._fxSwipe,FxSlots.RIGHT_HAND))).on(AnimationEventKey.SOUND).run(playSound(AudioConfiguration.FX,this.loserHitSound(param1,param3)).volume(_loc9_)).on(AnimationEventKey.STRIKE).run(this.loserHitNode(param1,param2,param3,param4));
         simpleMovement(param1,param2,this.hitAndRunDuration);
      }
      
      private function hitAndRunMotionless(param1:ParticipantData, param2:IBoufbowlerReference, param3:ParticipantData, param4:IBoufbowlerReference, param5:Boolean) : void
      {
         var _loc6_:int = param1.hasBall ? param1.side : param3.side;
         var _loc7_:String = param3.isDodging ? gaugeFx(this._loserStrength,Element.FIRE) : gaugeFx(this._loserStrength,Element.EARTH);
         var _loc8_:String = gaugeFx(this._winnerStrength,Element.EARTH);
         var _loc9_:HexPoint = gridInterm(param1.startPosition,param3.startPosition);
         var _loc10_:int = hexaAngle(_loc9_.vectorTo(param3.startPosition));
         var _loc11_:Number = ScriptConstants.VOLUME_FX_FOCUSED;
         this.loserAnimNode(param1,param3,param4);
         sequence(param2.playAnimation(BoufbowlerAnimKeys.TACLE_OK).facing(_loc10_).on(AnimationEventKey.FREEZE).run(importantActionDisplayNode(param5,_loc6_,this._zoomFactor,param2,param4,_loc8_,_loc7_)).on(AnimationEventKey.FX).run(param2.playFx(this._fxTackle,FxSlots.CUSTOM)).on(AnimationEventKey.SOUND).run(playSound(AudioConfiguration.FX,this.loserHitSound(param1,param3)).volume(_loc11_)).on(AnimationEventKey.STRIKE).run(group(param2.moveToPoint(_loc9_).duration(0),this.loserHitNode(param1,param2,param3,param4))),winnerReplaceNode());
      }
   }
}

