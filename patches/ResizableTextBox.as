package com.ankamagames.xgaming.ui.components
{
   import flash.display.Sprite;
   import flash.text.StyleSheet;
   import flash.text.TextField;
   import flash.text.TextFieldAutoSize;
   import com.ankamagames.boufbowl.BoufbowlClient;

   public class ResizableTextBox extends FlashInstanceContainer
   {

      private var _label:TextField;

      private var _textPadding:Padding;

      private var _textBackground:Sprite;

      public function ResizableTextBox()
      {
         super();
         this.init();
      }

      public function setHTMLText(param1:String) : void
      {
         this._label.htmlText = param1;
         this.textChanged();
      }

      public function setStyleSheet(param1:StyleSheet) : void
      {
         this._label.styleSheet = param1;
         this.textChanged();
      }

      public function forceCenterBackground() : void
      {
         this.textChanged(true);
      }

      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         this._textBackground = getFlashInstance("textBackgroundInstance",Sprite);
         this._label = getFlashInstance("labelInstance",TextField);
      }

      private function textChanged(param1:Boolean = false) : void
      {
         if(BoufbowlClient.ruffleRuntime)
         {
            this._label.height = Math.ceil(this._label.textHeight + 4);
            var panelHeight:Number = this._label.height + this._textPadding.top + (param1 ? this._textPadding.top : this._textPadding.bottom);
            var panelWidth:Number = this._label.width + this._textPadding.left + this._textPadding.right;
            this._textBackground.graphics.clear();
            this._textBackground.graphics.lineStyle(1,0xb1ae86);
            this._textBackground.graphics.beginFill(0xffffe8);
            this._textBackground.graphics.drawRoundRect(0,0,panelWidth,panelHeight,8);
            this._textBackground.graphics.endFill();
            return;
         }
         this._textBackground.height = this._label.height + this._textPadding.top + (param1 ? this._textPadding.top : this._textPadding.bottom);
      }

      private function init() : void
      {
         this.initLabel();
      }

      private function initLabel() : void
      {
         this._textPadding = new Padding(this._label.y,this._textBackground.width - this._label.x - this._label.width,this._textBackground.height - this._label.y - this._label.height,this._label.x);
         if(BoufbowlClient.ruffleRuntime)
         {
            // Replace only the stretched background; retain the original label,
            // HTML links and message-box button/event contracts.
            var replacement:Sprite = new Sprite();
            replacement.mouseEnabled = false;
            var index:int = getChildIndex(this._textBackground);
            removeChild(this._textBackground);
            this._textBackground = replacement;
            addChildAt(replacement,index);
            // Timeline backgrounds have centered registration points. Use a
            // common top-left origin so autosizing cannot offset the panel
            // away from its text or leave buttons outside the background.
            this._textPadding = new Padding(24,24,64,24);
            this._label.x = 24;
            this._label.y = 24;
            this._label.width = 512;
            this._label.wordWrap = this._label.multiline = true;
            this._label.autoSize = TextFieldAutoSize.LEFT;
            this._label.height = 0;
            return;
         }
         this._label.wordWrap = this._label.multiline = true;
         this._label.autoSize = TextFieldAutoSize.CENTER;
         this._label.height = 0;
      }
   }
}
