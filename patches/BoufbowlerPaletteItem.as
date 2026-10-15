package com.ankamagames.boufbowl.client.premiumservice.common.model.item
{
   import com.ankamagames.boufbowl.protocol.Gender;
   import flash.errors.IllegalOperationError;
   
   public class BoufbowlerPaletteItem extends BasePaletteItem
   {
      
      public static const HAIR_COLOR:uint = BasePaletteItem.FIRST_COLOR;
      
      public static const EYE_COLOR:uint = BasePaletteItem.SECOND_COLOR;
      
      public static const SKIN_COLOR:uint = BasePaletteItem.THIRD_COLOR;
      
      private var _defaultForClass:int;
      
      private var _defaultForUniqueCharacter:int;
      
      public function BoufbowlerPaletteItem(param1:int, param2:int, param3:int, param4:int, param5:int, param6:Array, param7:Array, param8:Array)
      {
         super(param1,param2,param3,param6,param7,param8);
         this._defaultForClass = param4;
         this._defaultForUniqueCharacter = param5;
      }
      
      public function get hairColors() : Array
      {
         return _firstColors;
      }
      
      public function get eyeColors() : Array
      {
         return _secondColors;
      }
      
      public function get skinColors() : Array
      {
         return _thirdColors;
      }
      
      public function get isDefaultForClass() : Boolean
      {
         return this._defaultForClass != 0;
      }
      
      public function get defaultForClass() : int
      {
         if(!this.isDefaultForClass)
         {
            throw new IllegalOperationError("defaultForClass is not set");
         }
         return this._defaultForClass;
      }
      
      public function get isDefaultForUniqueCharacter() : Boolean
      {
         return this._defaultForUniqueCharacter != 0;
      }
      
      public function get defaultForUniqueCharacter() : int
      {
         if(!this.isDefaultForUniqueCharacter)
         {
            throw new IllegalOperationError("defaultForUniqueCharacter is not set");
         }
         return this._defaultForUniqueCharacter;
      }
      
      public function getDefaultHairColorId(param1:int, param2:int) : int
      {
         return param1 == 0 && param2 == Gender.FEMALE ? 1 : 0;
      }
      
      public function getDefaultEyeColorId(param1:int, param2:int) : int
      {
         return param1 == 0 && param2 == Gender.FEMALE ? 1 : 0;
      }
      
      public function getDefaultSkinColorId(param1:int, param2:int) : int
      {
         return param1 == 0 && param2 == Gender.FEMALE ? 1 : 0;
      }
   }
}

