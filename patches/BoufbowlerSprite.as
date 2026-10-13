package com.ankamagames.boufbowl.resolution.display.animation
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import as3.collections.iterators.IMapIterator;
   import com.ankamagames.boufbowl.protocol.BoufbowlerClass;
   import com.ankamagames.boufbowl.protocol.Gender;
   import com.ankamagames.boufbowl.resolution.display.script.runner.BoufbowlerAnimKeys;
   import com.ankamagames.tiphon.display.TiphonSprite;
   import com.ankamagames.tiphon.types.look.TiphonEntityLook;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.errors.IllegalArgumentError;
   import flash.errors.IllegalOperationError;
   import flash.events.Event;
   import flash.events.EventDispatcher;
   
   public class BoufbowlerSprite extends EventDispatcher implements IBoufbowlerSprite
   {
      
      public static const ANIMATION_PROVIDER_CHANGED:String = "com.ankamagames.boufbowl.resolution.display.animation.BoufbowlerSprite.ANIMATION_PROVIDER_CHANGED";
      
      private static const LOOK_PATTERN:RegExp = /\{(.+)\|(.*)\|(.*)\}/i;
      
      private static const INDEXED_COLOR_PATTERN:RegExp = /(.+)=#(.+)/i;
      
      private var _entityLook:TiphonEntityLook;
      
      private var _sprite:TiphonSprite;
      
      private var _provider:TiphonAnimationProvider;
      
      private var _boufbowlerClass:int;
      
      private var _gender:int;
      
      private var _uniqueCharacter:uint;
      
      private var _colors:IMap;
      
      public function BoufbowlerSprite(param1:int, param2:int, param3:uint, param4:Color3, param5:Color3, param6:Color3, param7:Color3, param8:String = null)
      {
         super();
         this.init(param1,param2,param3,param4,param5,param6,param7,param8);
      }
      
      public static function createFromLook(param1:String, param2:uint = 0) : BoufbowlerSprite
      {
         var _loc13_:Array = null;
         var _loc14_:int = 0;
         var _loc15_:String = null;
         var _loc16_:Color3 = null;
         var _loc3_:Array = param1.match(LOOK_PATTERN);
         if(_loc3_.length != 4)
         {
            throw new IllegalArgumentError("The look string must have bones, skins and colors parts.");
         }
         var _loc4_:Array = String(_loc3_[2]).split(",");
         var _loc5_:Array = _loc3_[3] == "" ? [] : String(_loc3_[3]).split(",");
         var _loc6_:int = parseInt(_loc4_[1]);
         var _loc7_:int = parseInt(String(_loc4_[2]).substr(0,String(_loc4_[2]).length - 1));
         var _loc8_:Color3 = Color3.BLACK;
         var _loc9_:Color3 = Color3.BLACK;
         var _loc10_:Color3 = Color3.BLACK;
         var _loc11_:Color3 = Color3.BLACK;
         var _loc12_:int = 0;
         while(_loc12_ < _loc5_.length)
         {
            _loc13_ = String(_loc5_[_loc12_]).match(INDEXED_COLOR_PATTERN);
            _loc14_ = int(_loc13_[1]);
            _loc15_ = _loc13_[2];
            _loc16_ = Color3.fromRgbHexaString(_loc15_);
            switch(_loc14_)
            {
               case BoufbowlerColorIndex.HAIR:
                  _loc8_ = _loc16_;
                  break;
               case BoufbowlerColorIndex.EYES:
                  _loc9_ = _loc16_;
                  break;
               case BoufbowlerColorIndex.SKIN:
                  _loc10_ = _loc16_;
                  break;
               case BoufbowlerColorIndex.SHIRT:
                  _loc11_ = _loc16_;
                  break;
               case BoufbowlerColorIndex.TROUSER:
                  _loc11_ = _loc16_;
            }
            _loc12_++;
         }
         return new BoufbowlerSprite(_loc7_,_loc6_,param2,_loc8_,_loc9_,_loc10_,_loc11_);
      }
      
      public static function createFromCustomLook(param1:String) : BoufbowlerSprite
      {
         return new BoufbowlerSprite(BoufbowlerClass.IOP,Gender.MALE,0,Color3.BLACK,Color3.BLACK,Color3.BLACK,Color3.BLACK,param1);
      }
      
      public function get boufbowlerClass() : int
      {
         return this._boufbowlerClass;
      }
      
      public function set boufbowlerClass(param1:int) : void
      {
         this.release();
         this._boufbowlerClass = param1;
         this._entityLook = TiphonEntityLook.fromString(this.buildEntity());
         dispatchEvent(new Event(ANIMATION_PROVIDER_CHANGED));
      }
      
      public function get gender() : int
      {
         return this._gender;
      }
      
      public function get isUniqueCharacter() : Boolean
      {
         return this._uniqueCharacter != 0;
      }
      
      public function get uniqueCharacter() : uint
      {
         if(!this.isUniqueCharacter)
         {
            throw new IllegalOperationError("uniqueCharacter is not set");
         }
         return this._uniqueCharacter;
      }
      
      public function get colors() : IMap
      {
         return this._colors;
      }
      
      public function get hasBall() : Boolean
      {
         return this._provider.hasBall();
      }
      
      public function release() : void
      {
         if(this._sprite != null)
         {
            this._sprite.destroy();
         }
         if(this._provider != null)
         {
            this._provider.destroy();
         }
         this._sprite = null;
         this._provider = null;
      }
      
      public function getAnimationProvider() : IAnimationProvider
      {
         if(this._sprite == null)
         {
            this._sprite = new TiphonSprite(this._entityLook);
         }
         if(this._provider == null)
         {
            this._provider = new TiphonAnimationProvider(this._sprite,BoufbowlerAnimKeys.DEFAULT);
         }
         return this._provider;
      }
      
      private function init(param1:int, param2:int, param3:uint, param4:Color3, param5:Color3, param6:Color3, param7:Color3, param8:String) : void
      {
         this._boufbowlerClass = param1;
         this._gender = param2;
         this._uniqueCharacter = param3;
         this._colors = new Map();
         this._colors.addItem(BoufbowlerColorIndex.HAIR,param4);
         this._colors.addItem(BoufbowlerColorIndex.EYES,param5);
         this._colors.addItem(BoufbowlerColorIndex.SKIN,param6);
         this._colors.addItem(BoufbowlerColorIndex.SHIRT,param7);
         this._colors.addItem(BoufbowlerColorIndex.TROUSER,param7);
         this._entityLook = TiphonEntityLook.fromString(param8 != null ? param8 : this.buildEntity());
         var skins:Vector.<uint> = this._entityLook.getSkins();
         if(skins != null)
         {
            this._entityLook.resetSkins();
            for each(var skin:uint in skins)
            {
               if([0,1,2,11,12,32,42,61].indexOf(skin) < 0)
               {
                  if(skin >= 501) continue;
                  skin = this._gender == 2 ? 12 : 11;
               }
               this._entityLook.addSkin(skin);
            }
         }
      }
      
      private function buildEntity() : String
      {
         var _loc4_:Color3 = null;
         var _loc5_:uint = 0;
         var _loc1_:String = "{0|0,";
         _loc1_ += this._gender.toString();
         _loc1_ += ",";
         var requestedSkin:int = parseInt(this._boufbowlerClass.toString() + this._gender.toString());
         var available:Array = [11,12,32,42,61];
         var heroAvailable:Boolean = false;
         var renderSkin:int = requestedSkin;
         if(this.isUniqueCharacter && !heroAvailable || available.indexOf(requestedSkin) < 0)
            renderSkin = this._gender == 2 ? 12 : 11;
         _loc1_ += renderSkin.toString();
         if(this.isUniqueCharacter && heroAvailable)
         {
            _loc1_ += "," + this.uniqueCharacter;
         }
         _loc1_ += "|";
         var _loc2_:Boolean = true;
         var _loc3_:IMapIterator = this._colors.getMapIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            _loc5_ = _loc3_.getKey();
            if(_loc2_)
            {
               _loc2_ = false;
            }
            else
            {
               _loc1_ += ",";
            }
            _loc1_ += _loc5_.toString() + "=#" + _loc4_.toRgbHexaString();
         }
         return _loc1_ + "}";
      }
   }
}
