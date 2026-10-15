package com.ankamagames.xgaming.ui.components
{
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.geom.Rectangle;
   import flash.geom.Point;
   import flash.system.Capabilities;
   
   public class Slider extends BaseComponent
   {
      
      public static const MAX_VALUE:Number = 1;
      
      private var _thumb:Button;
      
      private var _track:BaseComponent;
      
      private var _colorableThumb:ColorableZone;
      
      private var _value:Number;
      
      private var _dragging:Boolean;
      
      private var _internalWidth:Number;
      
      public function Slider()
      {
         super();
         this.init();
      }
      
      public function get thumbColor() : uint
      {
         return this._colorableThumb.color;
      }
      
      public function set thumbColor(param1:uint) : void
      {
         this._colorableThumb.color = param1;
      }
      
      public function get value() : Number
      {
         return this._value;
      }
      
      public function set value(param1:Number) : void
      {
         this.internalSetValue(param1);
         this.updateThumbPosition();
      }
      
      override public function get width() : Number
      {
         return this._internalWidth;
      }
      
      override public function set width(param1:Number) : void
      {
         if(this._internalWidth == param1)
         {
            return;
         }
         this._internalWidth = param1;
         this._track.width = this._internalWidth + 2 * Math.abs(this._track.x);
         this.updateThumbPosition();
      }
      
      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         this._colorableThumb = getFlashInstance("thumb.arrow.colorableZone",ColorableZone) as ColorableZone;
         this._thumb = getFlashInstance("thumb",Button) as Button;
         this._track = getFlashInstance("track",BaseComponent) as BaseComponent;
      }
      
      private function internalSetValue(param1:Number) : void
      {
         this._value = param1;
         this._thumb.setTooltip(this._value.toFixed(2));
      }
      
      private function init() : void
      {
         this.internalSetValue(0);
         this._dragging = false;
         this._internalWidth = this._track.width - 2 * Math.abs(this._track.x);
         addEventListener(Event.ADDED_TO_STAGE,this.addedToStage,false,0,true);
         addEventListener(Event.REMOVED_FROM_STAGE,this.removedFromStage,false,0,true);
      }
      
      private function addedToStage(param1:Event) : void
      {
         this.addListeners();
      }
      
      private function removedFromStage(param1:Event) : void
      {
         this.clearDrag();
         this.removeListeners();
      }
      
      private function clearDrag() : void
      {
         if(!this._dragging)
         {
            return;
         }
         this._thumb.stopDrag();
         this._dragging = false;
      }
      
      private function addListeners() : void
      {
         this._thumb.addEventListener(MouseEvent.MOUSE_DOWN,this.thumbMouseDown);
         this._track.addEventListener(MouseEvent.CLICK,this.trackClick);
         stage.addEventListener(MouseEvent.MOUSE_UP,this.mouseUp);
         stage.addEventListener(MouseEvent.MOUSE_MOVE,this.mouseMove);
      }
      
      private function removeListeners() : void
      {
         this._thumb.removeEventListener(MouseEvent.MOUSE_DOWN,this.thumbMouseDown);
         this._track.removeEventListener(MouseEvent.CLICK,this.trackClick);
         stage.removeEventListener(MouseEvent.MOUSE_UP,this.mouseUp);
         stage.removeEventListener(MouseEvent.MOUSE_MOVE,this.mouseMove);
      }
      
      private function thumbMouseDown(param1:MouseEvent) : void
      {
         this._dragging = true;
         this._thumb.startDrag(false,new Rectangle(0,0,this._internalWidth,0));
      }
      
      private function trackClick(param1:MouseEvent) : void
      {
         var _loc2_:Number = param1.stageX - x;
         if(Capabilities.playerType == "PlugIn")
            _loc2_ = globalToLocal(new Point(param1.stageX,param1.stageY)).x;
         if(_loc2_ < 0 || _loc2_ > this._internalWidth)
         {
            return;
         }
         this.value = _loc2_ * MAX_VALUE / this._internalWidth;
      }
      
      private function mouseUp(param1:MouseEvent) : void
      {
         this.clearDrag();
      }
      
      private function mouseMove(param1:MouseEvent) : void
      {
         if(!this._dragging)
         {
            return;
         }
         this.internalSetValue(this._thumb.x * MAX_VALUE / this._internalWidth);
      }
      
      private function updateThumbPosition() : void
      {
         this._thumb.x = this._internalWidth * this._value / MAX_VALUE;
      }
   }
}

