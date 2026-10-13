package com.ankamagames.boufbowl.resolution.display.model.swfdata
{
   import com.ankamagames.xgaming.utils.load.SwfRegistry;
   import flash.display.Sprite;
   
   public class SwfSprite
   {
      
      public static const BOUFBALL:SwfSprite = new SwfSprite("app:/assets/sprites/boufball.swf","ball");
      
      public static const BOUFBALL_SHADOW:SwfSprite = new SwfSprite("app:/assets/sprites/boufball.swf","shadow");
      
      private var _swfFile:String;
      
      private var _exportName:String;
      
      public function SwfSprite(param1:String, param2:String)
      {
         super();
         this._swfFile = param1;
         this._exportName = param2;
      }
      
      public function get swfFile() : String
      {
         return this._swfFile;
      }
      
      public function get exportName() : String
      {
         return this._exportName;
      }
      
      public function createSprite(param1:SwfRegistry) : Sprite
      {
         var _loc2_:Sprite = param1.instanciate(this.swfFile,this.exportName) as Sprite;
         if(_loc2_ == null)
         {
            throw new Error("On a pas réussi à instancier le clip " + this.toString());
         }
         return _loc2_;
      }
      
      public function toString() : String
      {
         return this._swfFile + " export : " + this.exportName;
      }
   }
}

