package com.ankamagames.boufbowl.resolution.display.model.swfdata
{
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.resolution.display.animation.IEquipementData;
   import com.ankamagames.xgaming.utils.load.SwfRegistry;
   import flash.display.Sprite;
   
   public class EquipementData implements IEquipementData
   {
      
      public static const CARRIED_BOUFBALL:IEquipementData = new EquipementData("app:/assets/sprites/boufball.swf","boufballe",Vector.<int>([0,1,2,3,4,5,6,7]));
      
      private var _swfFile:String;
      
      private var _exportNameBase:String;
      
      private var _directions:Vector.<int>;
      
      private var _equipementSprites:Vector.<Sprite>;
      
      public function EquipementData(param1:String, param2:String, param3:Vector.<int>)
      {
         super();
         this._swfFile = param1;
         this._exportNameBase = param2;
         this._directions = param3;
      }
      
      public function init(param1:SwfRegistry) : void
      {
         var _loc2_:int = 0;
         var _loc3_:Sprite = null;
         this._equipementSprites = new Vector.<Sprite>();
         for each(_loc2_ in this._directions)
         {
            if(!param1.isLoaded(this._swfFile))
            {
               throw new IllegalStateError(this._swfFile + " was not properly loaded");
            }
            _loc3_ = param1.instanciate(this._swfFile,this._exportNameBase + "_" + _loc2_) as Sprite;
            if(_loc3_ == null)
            {
               throw new Error("On a pas réussi à instancier le clip " + this._exportNameBase + "_" + _loc2_);
            }
            this._equipementSprites[_loc2_] = _loc3_;
         }
      }
      
      public function getSprite(param1:int) : Sprite
      {
         return this._equipementSprites[param1];
      }
      
      public function getDirections() : Vector.<int>
      {
         return this._directions;
      }
   }
}

