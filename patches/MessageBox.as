package com.ankamagames.xgaming.ui.components
{
   import flash.geom.Point;
   import flash.text.StyleSheet;
   import com.ankamagames.boufbowl.BoufbowlClient;

   public class MessageBox extends FlashInstanceContainer
   {

      private static const DEFAULT_SIZE:Point = new Point(1024,600);

      private var _buttonPaddingBottom:Number;

      private var _defaultFirstButtonX:Number;

      private var _defaultSecondButtonX:Number;

      private var _resizableText:ResizableTextBox;

      private var _firstButton:Button;

      private var _secondButton:Button;

      public function MessageBox()
      {
         super();
         this.init();
      }

      public function get firstButton() : Button
      {
         return this._firstButton;
      }

      public function get secondButton() : Button
      {
         return this._secondButton;
      }

      public function setStyleSheet(param1:StyleSheet) : void
      {
         this._resizableText.setStyleSheet(param1);
         this.updateLayout();
      }

      protected function internalUpdate(param1:String, param2:String, param3:String = null) : void
      {
         this._resizableText.setHTMLText(param1);
         this._firstButton.componentLabel = param2 || "";
         this._secondButton.componentLabel = param3 || "";
         this._firstButton.visible = param2 != null;
         this._secondButton.visible = param3 != null;
         this.updateLayout();
      }

      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         this._firstButton = getFlashInstance("firstButtonInstance",Button);
         this._secondButton = getFlashInstance("secondButtonInstance",Button);
         this._resizableText = getFlashInstance("resizableTextInstance",ResizableTextBox);
      }

      private function init() : void
      {
         this._defaultFirstButtonX = this._firstButton.x;
         this._defaultSecondButtonX = this._secondButton.x;
         this._buttonPaddingBottom = this._resizableText.y + this._resizableText.height - this._firstButton.y;
      }

      private function updateLayout() : void
      {
         if(BoufbowlClient.ruffleRuntime)
         {
            if(!this._firstButton.visible && !this._secondButton.visible)
               this._resizableText.forceCenterBackground();
            this._resizableText.x = (DEFAULT_SIZE.x - this._resizableText.width) / 2;
            this._resizableText.y = (DEFAULT_SIZE.y - this._resizableText.height) / 2;
            var buttonsWidth:Number = (this._firstButton.visible ? this._firstButton.width : 0) +
               (this._secondButton.visible ? this._secondButton.width : 0) +
               (this._firstButton.visible && this._secondButton.visible ? 16 : 0);
            var buttonX:Number = (DEFAULT_SIZE.x - buttonsWidth) / 2;
            if(this._firstButton.visible)
            {
               this._firstButton.x = buttonX;
               this._firstButton.y = this._resizableText.y + this._resizableText.height - this._firstButton.height - 16;
               buttonX += this._firstButton.width + 16;
            }
            if(this._secondButton.visible)
            {
               this._secondButton.x = buttonX;
               this._secondButton.y = this._resizableText.y + this._resizableText.height - this._secondButton.height - 16;
            }
            return;
         }
         this._resizableText.x = (DEFAULT_SIZE.x - this._resizableText.width) / 2;
         this._resizableText.y = (DEFAULT_SIZE.y - this._resizableText.height) / 2;
         if(this._firstButton.visible)
         {
            this._firstButton.x = this._secondButton.visible ? this._defaultFirstButtonX : (DEFAULT_SIZE.x - this._firstButton.width) / 2;
            this._firstButton.y = this._resizableText.y + this._resizableText.height - this._buttonPaddingBottom;
         }
         if(this._secondButton.visible)
         {
            this._secondButton.x = this._defaultSecondButtonX;
            this._secondButton.y = this._resizableText.y + this._resizableText.height - this._buttonPaddingBottom;
         }
         if(!this._firstButton.visible && !this._secondButton.visible)
         {
            this._resizableText.forceCenterBackground();
         }
      }
   }
}
