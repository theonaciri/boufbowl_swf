package com.ankamagames.xgaming.ui.components
{
   import com.ankamagames.xgaming.ui.event.ShowTooltipEvent;
   import flash.display.Sprite;
   import flash.display.DisplayObject;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.filters.ColorMatrixFilter;
   
   public class BaseComponent extends FlashInstanceContainer
   {
      
      private static const DISABLED_FILTER:ColorMatrixFilter = new ColorMatrixFilter([0.699,0,0,0,-1.95,0,0.699,0,0,-1.95,0,0,0.699,0,-1.95,0,0,0,1,0]);
      
      private var _mouseChildren:Boolean;
      
      private var _initFilters:Array;
      
      private var _tooltipText:String;
      
      private var _tooltipGraphicElements:Vector.<Function>;
      
      public static const TOOLTIP_CONTENT_CHANGED:String = "componentTooltipContentChanged";

      private var _tapTooltipRequested:Boolean;

      private var _compEnabled:Boolean;
      
      public function BaseComponent()
      {
         super();
         this.init();
      }
      
      public function get tooltip() : String
      {
         return this._tooltipText;
      }
      
      public function get tapTooltipRequested() : Boolean
      {
         return this._tapTooltipRequested;
      }

      public function get compEnabled() : Boolean
      {
         return this._compEnabled;
      }
      
      public function set compEnabled(param1:Boolean) : void
      {
         if(this._compEnabled == param1)
         {
            return;
         }
         if(!param1) dispatchEvent(new Event(TOOLTIP_CONTENT_CHANGED));
         this._compEnabled = param1;
         mouseEnabled = this._compEnabled;
         this.updateMouseChildren();
         var _loc2_:Array = this._initFilters.slice();
         if(!this._compEnabled)
         {
            _loc2_.push(DISABLED_FILTER);
         }
         filters = _loc2_;
      }
      
      override public function set mouseChildren(param1:Boolean) : void
      {
         this._mouseChildren = param1;
         this.updateMouseChildren();
      }
      
      public function setTooltip(param1:String, param2:Vector.<Function> = null) : void
      {
         if(this._tooltipText != param1) dispatchEvent(new Event(TOOLTIP_CONTENT_CHANGED));
         this._tooltipText = param1;
         this._tooltipGraphicElements = param2;
         this.manageListener();
      }
      
      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         this.initHitArea();
      }
      
      private function updateMouseChildren() : void
      {
         super.mouseChildren = this._compEnabled && this._mouseChildren;
      }
      
      private function initHitArea() : void
      {
         var _loc1_:Sprite = getFlashInstance("hitzone",Sprite,false);
         if(_loc1_ != null)
         {
            hitArea = _loc1_;
            hitArea.mouseEnabled = hitArea.mouseChildren = false;
            hitArea.visible = false;
         }
         else
         {
            hitArea = null;
         }
      }
      
      private function init() : void
      {
         this._initFilters = filters;
         this._mouseChildren = super.mouseChildren;
         this.compEnabled = true;
      }
      
      private function manageListener() : void
      {
         var hasTooltip:Boolean = this._tooltipText != null && this._tooltipText.length != 0;
         if(hasTooltip)
         {
            addEventListener(MouseEvent.ROLL_OVER,this.rollOver,false,0,true);
            // Ordinary button actions run first. Never cancel or swallow their click.
            addEventListener(MouseEvent.CLICK,this.showOnTap,false,-100,true);
         }
         else
         {
            removeEventListener(MouseEvent.ROLL_OVER,this.rollOver);
            removeEventListener(MouseEvent.CLICK,this.showOnTap);
         }
      }

      private function showOnTap(event:MouseEvent) : void
      {
         if(!this._compEnabled || stage == null || this._tooltipText == null || this._tooltipText.length == 0) return;
         // A nested tooltip belongs to the deepest enabled component, not its parent.
         var source:DisplayObject = event.target as DisplayObject;
         while(source != null && source != this)
         {
            var component:BaseComponent = source as BaseComponent;
            if(component != null && component.compEnabled && component.tooltip != null && component.tooltip.length != 0) return;
            source = source.parent;
         }
         this._tapTooltipRequested = true;
         try
         {
            dispatchEvent(new ShowTooltipEvent(this,this._tooltipText,this._tooltipGraphicElements));
         }
         finally
         {
            this._tapTooltipRequested = false;
         }
      }

      private function rollOver(param1:MouseEvent) : void
      {
         dispatchEvent(new ShowTooltipEvent(this,this._tooltipText,this._tooltipGraphicElements));
      }
   }
}

