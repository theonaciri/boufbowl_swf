package com.ankamagames.boufbowl.ui.components.teampanel
{
   import com.ankamagames.boufbowl.ui.components.order.OrderClassIcon;
   import com.ankamagames.xgaming.ui.components.BaseComponent;
   import com.ankamagames.xgaming.ui.event.ShowTooltipEvent;
   import flash.events.Event;
   import flash.events.MouseEvent;
   
   public class OrderSpellTooltipHandler extends BaseComponent
   {
      
      public static const TOOLTIP_CONTENT_CHANGED:String = "powerTooltipContentChanged";

      private var _iconSprite:OrderClassIcon;

      private var _tapRequested:Boolean;
      
      public function OrderSpellTooltipHandler()
      {
         super();
         addEventListener(MouseEvent.CLICK, this.showOnTap, false, 0, true);
      }

      public function get tapTooltipRequested() : Boolean
      {
         return this._tapRequested;
      }

      override public function setTooltip(text:String, elements:Vector.<Function> = null) : void
      {
         if(tooltip != text) dispatchEvent(new Event(TOOLTIP_CONTENT_CHANGED));
         super.setTooltip(text, elements);
      }

      private function showOnTap(event:MouseEvent) : void
      {
         if(!compEnabled || tooltip == null || tooltip.length == 0) return;
         this._tapRequested = true;
         try
         {
            dispatchEvent(new ShowTooltipEvent(this, tooltip, null));
         }
         finally
         {
            this._tapRequested = false;
         }
      }
      
      public function set classIcon(param1:int) : void
      {
         this._iconSprite.classIcon = param1;
      }
      
      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         this._iconSprite = getFlashInstance("iconSprite",OrderClassIcon) as OrderClassIcon;
      }
   }
}

