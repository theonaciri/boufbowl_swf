package com.ankamagames.boufbowl.ui.components.chat
{
   import com.ankamagames.xgaming.ui.components.Button;
   import com.ankamagames.xgaming.ui.components.ColorableZone;

   public class ChannelButton extends Button
   {

      private var _colorable:ColorableZone;

      private var _color:uint;

      public function ChannelButton()
      {
         super();
      }

      public function get color() : uint
      {
         return this._color;
      }

      public function set color(param1:uint) : void
      {
         this._color = param1;
         this.applyColor();
      }

      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         this._colorable = getFlashInstance("star.color",ColorableZone) as ColorableZone;
      }

      override protected function updateState() : void
      {
         super.updateState();
         this.applyColor();
      }

      private function applyColor() : void
      {
         // Button timeline changes may replace the named star instance.
         // Apply the stored channel color to the currently displayed shape.
         this._colorable = getFlashInstance("star.color",ColorableZone) as ColorableZone;
         this._colorable.color = this._color;
      }
   }
}

