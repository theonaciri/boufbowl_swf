package com.ankamagames.xgaming.ui.components.scrolling
{
   import com.ankamagames.xgaming.ui.components.Button;
   import com.ankamagames.xgaming.ui.components.FlashInstanceContainer;
   import flash.display.Sprite;
   import flash.display.BitmapData;
   import flash.geom.Matrix;
   import flash.geom.Rectangle;
   import flash.system.Capabilities;

   public class ScrollIndicator extends FlashInstanceContainer
   {
      private static const WEB_SKIN_SCALE:Number = 3;

      public var webThumbRendering:Boolean = false;

      private var _webThumb:Sprite;

      private var _webSkin:BitmapData;

      private var _webSkinBounds:Rectangle;

      private var _webCapTop:Number;

      private var _webCapBottom:Number;

      private var _marker:Button;

      private var _background:Sprite;

      public function ScrollIndicator()
      {
         super();
         this.webThumbRendering = Capabilities.playerType == "PlugIn";
         this._background.useHandCursor = this._background.buttonMode = true;
      }

      public function get marker() : Button
      {
         return this._marker;
      }

      public function get background() : Sprite
      {
         return this._background;
      }

      public function update(param1:Number, param2:Number, param3:Number) : void
      {
         if(this.webThumbRendering)
         {
            param1 = isNaN(param1) ? 0 : Math.max(0,Math.min(1,param1));
            param2 = isNaN(param2) ? 1 : Math.max(0,Math.min(1,param2));
            param3 = Math.min(this._background.height,Math.max(0,param3));
         }
         var _loc4_:Number = param2 * this._background.height;
         if(_loc4_ > this._background.height)
         {
            this._marker.height = this._background.height;
         }
         else if(_loc4_ < param3)
         {
            this._marker.height = param3;
         }
         else
         {
            this._marker.height = _loc4_;
         }
         this._marker.y = param1 * (this._background.height - this._marker.height);
         if(this.webThumbRendering) this.drawWebThumb();
      }

      private function drawWebThumb() : void
      {
         if(this._webSkin == null)
         {
            // Capture the original unscaled skin; Ruffle stretches its caps
            // when the parent button's height is changed through scale9Grid.
            var oldScaleX:Number = this._marker.scaleX;
            var oldScaleY:Number = this._marker.scaleY;
            this._marker.scaleX = this._marker.scaleY = 1;
            this._webSkinBounds = this._marker.getBounds(this._marker);
            var grid:Rectangle = this._marker.scale9Grid;
            this._webSkin = new BitmapData(Math.max(1,Math.ceil(this._webSkinBounds.width * WEB_SKIN_SCALE)),
               Math.max(1,Math.ceil(this._webSkinBounds.height * WEB_SKIN_SCALE)),true,0);
            try
            {
               this._webSkin.draw(this._marker,new Matrix(WEB_SKIN_SCALE,0,0,WEB_SKIN_SCALE,
                  -this._webSkinBounds.x * WEB_SKIN_SCALE,-this._webSkinBounds.y * WEB_SKIN_SCALE));
            }
            finally
            {
               this._marker.scaleX = oldScaleX;
               this._marker.scaleY = oldScaleY;
            }
            this._webCapTop = grid != null ? (grid.y - this._webSkinBounds.y) * WEB_SKIN_SCALE : Math.min(5 * WEB_SKIN_SCALE,this._webSkin.height / 3);
            this._webCapTop = Math.max(1,Math.min(this._webSkin.height - 2,this._webCapTop));
            this._webCapBottom = grid != null ? this._webSkin.height - (grid.bottom - this._webSkinBounds.y) * WEB_SKIN_SCALE : this._webCapTop;
            this._webCapBottom = Math.max(1,Math.min(this._webSkin.height - this._webCapTop - 1,this._webCapBottom));
            this._webThumb = new Sprite();
            this._webThumb.mouseEnabled = this._webThumb.mouseChildren = false;
            addChild(this._webThumb);
         }
         // Keep the original button as the drag/hit target, with its existing
         // events and dimensions. The separate skin never intercepts input.
         this._marker.alpha = 0;
         var targetWidth:Number = this._marker.width;
         var targetHeight:Number = this._marker.height;
         this._webThumb.x = this._marker.x + this._webSkinBounds.x * this._marker.scaleX;
         this._webThumb.y = this._marker.y + this._webSkinBounds.y * this._marker.scaleY;
         var capScale:Number = Math.min(1,targetHeight * WEB_SKIN_SCALE / (this._webCapTop + this._webCapBottom));
         var top:Number = this._webCapTop * capScale / WEB_SKIN_SCALE;
         var bottom:Number = this._webCapBottom * capScale / WEB_SKIN_SCALE;
         this._webThumb.graphics.clear();
         this.drawWebSlice(0,this._webCapTop,0,top,targetWidth);
         this.drawWebSlice(this._webCapTop,this._webSkin.height - this._webCapTop - this._webCapBottom,
            top,targetHeight - top - bottom,targetWidth);
         this.drawWebSlice(this._webSkin.height - this._webCapBottom,this._webCapBottom,
            targetHeight - bottom,bottom,targetWidth);
      }

      private function drawWebSlice(sourceY:Number, sourceHeight:Number, targetY:Number, targetHeight:Number, targetWidth:Number) : void
      {
         if(targetHeight <= 0 || sourceHeight <= 0) return;
         var scaleY:Number = targetHeight / sourceHeight;
         var matrix:Matrix = new Matrix(targetWidth / this._webSkin.width,0,0,scaleY,0,targetY - sourceY * scaleY);
         this._webThumb.graphics.beginBitmapFill(this._webSkin,matrix,false,true);
         this._webThumb.graphics.drawRect(0,targetY,targetWidth,targetHeight);
         this._webThumb.graphics.endFill();
      }

      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         this._marker = getFlashInstance("markerButton",Button);
         this._background = getFlashInstance("backgroundSprite",Sprite);
      }
   }
}
