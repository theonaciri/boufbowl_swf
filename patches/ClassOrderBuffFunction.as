package com.ankamagames.boufbowl.client.match.resolution.interactions
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.protocol.BoufbowlerClass;
   import com.ankamagames.boufbowl.protocol.ClassOrderTarget;
   import com.ankamagames.boufbowl.protocol.ZobalMask;
   import com.ankamagames.boufbowl.resolution.display.model.FxSlots;
   import com.ankamagames.boufbowl.resolution.display.model.FxSprites;
   import com.ankamagames.boufbowl.resolution.display.script.CommonInteractionFunctions;
   import com.ankamagames.boufbowl.resolution.display.script.InteractionRoles;
   import com.ankamagames.boufbowl.resolution.display.script.ParticipantData;
   import com.ankamagames.boufbowl.resolution.display.script.runner.BoufbowlerAnimKeys;
   import com.ankamagames.boufbowl.resolution.display.script.runner.IBoufbowlerReference;
   
   public class ClassOrderBuffFunction extends CommonInteractionFunctions
   {
      
      private const displaySpellDelay:int = 2000;
      
      private const targetFxDelay:int = 800;
      
      private var _boufbowlerClass:int;
      
      private var _targetList:Array;
      
      private var _zobalMask:Number;
      
      public function ClassOrderBuffFunction(param1:ParticipantData, param2:int, param3:Array = null, param4:Number = -1)
      {
         var _loc5_:IMap = new Map();
         _loc5_.addItem(InteractionRoles.ONLY_PARTICIPANT,param1);
         super(_loc5_);
         this._boufbowlerClass = param2;
         this._targetList = param3;
         this._zobalMask = param4 < 0 ? NaN : param4;
      }
      
      override public function buildNodes() : void
      {
         if(this._boufbowlerClass == BoufbowlerClass.ZOBAL && !isNaN(this._zobalMask))
         {
            this.playCasterSound();
            this.changeMask(this._zobalMask);
         }
         else
         {
            this.playCasterSound();
            this.casterFx();
            then();
            this.playTargetSound();
            this.targetFx();
            then();
            this.targetBuff();
         }
      }
      
      private function casterFx() : void
      {
         var _loc1_:IBoufbowlerReference = getBoufbowler(InteractionRoles.ONLY_PARTICIPANT);
         sequence(_loc1_.playAnimation(BoufbowlerAnimKeys.BERZERK).toStatic(BoufbowlerAnimKeys.STATIC_BERZERK),_loc1_.playFx(this.classOrderCasterFx(this._boufbowlerClass),this.classOrderFxSlot(this._boufbowlerClass)));
         sequence(_loc1_.addColorFX().duration(this.displaySpellDelay),_loc1_.setStatic(BoufbowlerAnimKeys.STATIC_FIRE));
      }
      
      private function targetFx() : void
      {
         var _loc1_:ClassOrderTarget = null;
         var _loc2_:IBoufbowlerReference = null;
         for each(_loc1_ in this._targetList)
         {
            _loc2_ = getBoufbowlerReference(_loc1_.boufbowlerId);
            sequence(_loc2_.addColorFX().duration(-1),_loc2_.playFx(this.classOrderTargetFx(this._boufbowlerClass),this.classOrderFxSlot(this._boufbowlerClass)),_loc2_.removeColorFX());
         }
      }
      
      private function targetBuff() : void
      {
         var target:ClassOrderTarget;
         var rounds:int=1;
         for each(target in this._targetList)rounds=Math.max(rounds,target.effectDeltas.length);
         for(var index:int=0;index<rounds;index++) {
            for each(target in this._targetList) {
               var value:Number=NaN;
               if(index<target.effectDeltas.length)value=Number(target.effectDeltas[index]);
               else if(index==0 && target.hasPreResolutionHitPointsDelta && target.preResolutionHitPointsDelta!=0)value=target.preResolutionHitPointsDelta;
               if(!isNaN(value) && value!=0) {
                  var actor:IBoufbowlerReference=getBoufbowlerReference(target.boufbowlerId);
                  actor.addOnomatopeia(getHpFxByDelta(int(value)));
                  com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.tracePowerNumber(target.boufbowlerId.toString(),int(value));
               }
            }
            wait(index+1<rounds ? 800 : 2000);
            if(index+1<rounds)then();
         }
      }

      private function playCasterSound() : void
      {
         playSound(AudioConfiguration.FX,this.classOrderCasterSound(this._boufbowlerClass));
      }
      
      private function playTargetSound() : void
      {
         if(!(this._boufbowlerClass == BoufbowlerClass.ZOBAL || this._boufbowlerClass == BoufbowlerClass.ECAFLIP || this._targetList.length == 0))
         {
            playSound(AudioConfiguration.FX,this.classOrderTargetSound(this._boufbowlerClass));
         }
      }
      
      private function changeMask(param1:int) : void
      {
         var _loc3_:int = 0;
         var _loc2_:IBoufbowlerReference = getBoufbowler(InteractionRoles.ONLY_PARTICIPANT);
         if(param1 == ZobalMask.CLASS)
         {
            _loc3_ = BoufbowlerClass.ZOBAL;
         }
         else if(param1 == ZobalMask.PSYCHO)
         {
            _loc3_ = BoufbowlerClass.ZOBAL + 1;
         }
         else if(param1 == ZobalMask.COWARD)
         {
            _loc3_ = BoufbowlerClass.ZOBAL + 2;
         }
         _loc2_.changeClassSkin(_loc3_);
         _loc2_.addColorFX().duration(-1);
         _loc2_.playFx(this.classOrderCasterFx(this._boufbowlerClass),this.classOrderFxSlot(this._boufbowlerClass));
         then();
         _loc2_.removeColorFX();
      }
      
      private function classOrderFxSlot(param1:int) : uint
      {
         if(param1 == BoufbowlerClass.ENIRIPSA)
         {
            return FxSlots.LEGS_FRONT;
         }
         return FxSlots.FACE;
      }
      
      private function classOrderCasterFx(param1:int) : String
      {
         var _loc2_:String = null;
         switch(param1)
         {
            case BoufbowlerClass.CRA:
               _loc2_ = FxSprites.CLASS_CASTER_CRA;
               break;
            case BoufbowlerClass.ECAFLIP:
               _loc2_ = FxSprites.CLASS_CASTER_ECAFLIP;
               break;
            case BoufbowlerClass.ENIRIPSA:
               _loc2_ = FxSprites.CLASS_CASTER_ENIRIPSA;
               break;
            case BoufbowlerClass.ENUTROF:
               _loc2_ = FxSprites.CLASS_CASTER_ENUTROF;
               break;
            case BoufbowlerClass.FECA:
               _loc2_ = FxSprites.CLASS_CASTER_FECA;
               break;
            case BoufbowlerClass.IOP:
               _loc2_ = FxSprites.CLASS_CASTER_IOP;
               break;
            case BoufbowlerClass.OSAMODAS:
               _loc2_ = FxSprites.CLASS_CASTER_OSAMODAS;
               break;
            case BoufbowlerClass.PANDAWA:
               _loc2_ = FxSprites.CLASS_CASTER_PANDAWA;
               break;
            case BoufbowlerClass.ROUBLARD:
               _loc2_ = FxSprites.CLASS_CASTER_ROUBLARD;
               break;
            case BoufbowlerClass.SACRIEUR:
               _loc2_ = FxSprites.CLASS_CASTER_SACRIEUR;
               break;
            case BoufbowlerClass.SADIDA:
               _loc2_ = FxSprites.CLASS_CASTER_SADIDA;
               break;
            case BoufbowlerClass.SRAM:
               _loc2_ = FxSprites.CLASS_CASTER_SRAM;
               break;
            case BoufbowlerClass.XELOR:
               _loc2_ = FxSprites.CLASS_CASTER_XELOR;
               break;
            case BoufbowlerClass.ZOBAL:
               _loc2_ = FxSprites.CLASS_CASTER_ZOBAL;
         }
         return _loc2_;
      }
      
      private function classOrderTargetFx(param1:int) : String
      {
         var _loc2_:String = null;
         switch(param1)
         {
            case BoufbowlerClass.CRA:
               _loc2_ = FxSprites.CLASS_TARGET_CRA;
               break;
            case BoufbowlerClass.ECAFLIP:
               _loc2_ = FxSprites.EMPTY;
               break;
            case BoufbowlerClass.ENIRIPSA:
               _loc2_ = FxSprites.CLASS_TARGET_ENIRIPSA;
               break;
            case BoufbowlerClass.ENUTROF:
               _loc2_ = FxSprites.CLASS_TARGET_ENUTROF;
               break;
            case BoufbowlerClass.FECA:
               _loc2_ = FxSprites.CLASS_TARGET_FECA;
               break;
            case BoufbowlerClass.IOP:
               _loc2_ = FxSprites.CLASS_TARGET_IOP;
               break;
            case BoufbowlerClass.OSAMODAS:
               _loc2_ = FxSprites.CLASS_TARGET_OSAMODAS;
               break;
            case BoufbowlerClass.PANDAWA:
               _loc2_ = FxSprites.CLASS_TARGET_PANDAWA;
               break;
            case BoufbowlerClass.ROUBLARD:
               _loc2_ = FxSprites.CLASS_TARGET_ROUBLARD;
               break;
            case BoufbowlerClass.SACRIEUR:
               _loc2_ = FxSprites.CLASS_TARGET_SACRIEUR;
               break;
            case BoufbowlerClass.SADIDA:
               _loc2_ = FxSprites.CLASS_TARGET_SADIDA;
               break;
            case BoufbowlerClass.SRAM:
               _loc2_ = FxSprites.CLASS_TARGET_SRAM;
               break;
            case BoufbowlerClass.XELOR:
               _loc2_ = FxSprites.CLASS_TARGET_XELOR;
               break;
            case BoufbowlerClass.ZOBAL:
               _loc2_ = FxSprites.EMPTY;
         }
         return _loc2_;
      }
      
      private function classOrderCasterSound(param1:int) : String
      {
         var _loc2_:String = null;
         switch(param1)
         {
            case BoufbowlerClass.CRA:
               _loc2_ = "interactions/caster_cra.mp3";
               break;
            case BoufbowlerClass.ECAFLIP:
               _loc2_ = "interactions/caster_ecaflip.mp3";
               break;
            case BoufbowlerClass.ENIRIPSA:
               _loc2_ = "interactions/caster_eniripsa.mp3";
               break;
            case BoufbowlerClass.ENUTROF:
               _loc2_ = "interactions/caster_enutrof.mp3";
               break;
            case BoufbowlerClass.FECA:
               _loc2_ = "interactions/caster_feca.mp3";
               break;
            case BoufbowlerClass.IOP:
               _loc2_ = "interactions/caster_iop.mp3";
               break;
            case BoufbowlerClass.OSAMODAS:
               _loc2_ = "interactions/caster_osamodas.mp3";
               break;
            case BoufbowlerClass.PANDAWA:
               _loc2_ = "interactions/caster_pandawa.mp3";
               break;
            case BoufbowlerClass.ROUBLARD:
               _loc2_ = "interactions/caster_roublard.mp3";
               break;
            case BoufbowlerClass.SACRIEUR:
               _loc2_ = "interactions/caster_sacrieur.mp3";
               break;
            case BoufbowlerClass.SADIDA:
               _loc2_ = "interactions/caster_sadida.mp3";
               break;
            case BoufbowlerClass.SRAM:
               _loc2_ = "interactions/caster_sram.mp3";
               break;
            case BoufbowlerClass.XELOR:
               _loc2_ = "interactions/caster_xelor.mp3";
               break;
            case BoufbowlerClass.ZOBAL:
               _loc2_ = "interactions/caster_zobal.mp3";
         }
         return _loc2_;
      }
      
      private function classOrderTargetSound(param1:int) : String
      {
         var _loc2_:String = null;
         switch(param1)
         {
            case BoufbowlerClass.CRA:
               _loc2_ = "interactions/bonus_target_cra.mp3";
               break;
            case BoufbowlerClass.ECAFLIP:
               _loc2_ = "";
               break;
            case BoufbowlerClass.ENIRIPSA:
               _loc2_ = "interactions/bonus_target_eniripsa.mp3";
               break;
            case BoufbowlerClass.ENUTROF:
               _loc2_ = "interactions/malus_target_enutrof.mp3";
               break;
            case BoufbowlerClass.FECA:
               _loc2_ = "interactions/bonus_target_feca.mp3";
               break;
            case BoufbowlerClass.IOP:
               _loc2_ = "interactions/bonus_target_iop.mp3";
               break;
            case BoufbowlerClass.OSAMODAS:
               _loc2_ = "interactions/malus_target_osamodas.mp3";
               break;
            case BoufbowlerClass.PANDAWA:
               _loc2_ = "interactions/malus_target_pandawa.mp3";
               break;
            case BoufbowlerClass.ROUBLARD:
               _loc2_ = "interactions/malus_target_roublard.mp3";
               break;
            case BoufbowlerClass.SACRIEUR:
               _loc2_ = "interactions/bonus_target_sacrieur.mp3";
               break;
            case BoufbowlerClass.SADIDA:
               _loc2_ = "interactions/bonus_target_sadida.mp3";
               break;
            case BoufbowlerClass.SRAM:
               _loc2_ = "interactions/bonus_target_sram.mp3";
               break;
            case BoufbowlerClass.XELOR:
               _loc2_ = "interactions/bonus_target_xelor.mp3";
               break;
            case BoufbowlerClass.ZOBAL:
               _loc2_ = "";
         }
         return _loc2_;
      }
   }
}

