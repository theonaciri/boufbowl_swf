package com.ankamagames.boufbowl.ui.components.tooltip
{
   import com.ankamagames.xgaming.ui.components.TextZone;
   import com.ankamagames.xgaming.utils.display.Color3;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import com.ankamagames.xgaming.ui.components.FlashInstanceContainer;
   import flash.display.Sprite;
   import flash.errors.IllegalOperationError;
   
   public class Tooltip extends Sprite
   {
      
      private var _textZone:TextZone;
      
      public function Tooltip()
      {
         super();
         this.init();
      }
      
      public function set fontFamily(param1:String) : void
      {
         this._textZone.defaultFontFamily = param1;
      }
      
      public function get backgroundSprite() : DisplayObject
      {
         if(!hasOwnProperty("_bcgSprite"))
         {
            throw new IllegalOperationError("An instance of Tooltip should have a DisplayObject named \'_bcgSprite\' !");
         }
         return this["_bcgSprite"] as DisplayObject;
      }
      
      public function setContent(param1:String, param2:Vector.<Function> = null) : void
      {
         this._textZone.setSize(this.textZonePlaceHolder.width,this.textZonePlaceHolder.height);
         this._textZone.setContent(param1,param2);
         this._textZone.updateNow();
         this.updateSize();
      }
      
      private function init() : void
      {
         this.textZonePlaceHolder.visible = false;
         this._textZone = new TextZone();
         this._textZone.defaultFontSize = 12;
         this._textZone.defaultTextColor = Color3.WHITE;
         this._textZone.x = this.textZonePlaceHolder.x;
         this._textZone.y = this.textZonePlaceHolder.y;
         addChild(this._textZone);
      }
      
      private function updateSize() : void
      {
         this.backgroundSprite.width = 2 * this._textZone.x + this._textZone.width;
         this.backgroundSprite.height = 2 * this._textZone.y + this._textZone.height;
         // Tooltip extends Sprite, so its skin never reaches the normal
         // FlashInstanceContainer repair pass. Keep its corners fixed in Ruffle.
         if(this.backgroundSprite is DisplayObjectContainer)
            FlashInstanceContainer.repairBrowserSkin(DisplayObjectContainer(this.backgroundSprite));
      }
      
      private function get textZonePlaceHolder() : Sprite
      {
         if(!hasOwnProperty("_textZonePlaceHolder"))
         {
            throw new IllegalOperationError("An instance of Tooltip should have a Sprite named \'_textZonePlaceHolder\' !");
         }
         return this["_textZonePlaceHolder"] as Sprite;
      }
   }
}

