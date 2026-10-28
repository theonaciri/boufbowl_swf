package com.ankamagames.boufbowl.client.application.tooltip
{
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.xgaming.ui.components.BaseComponent;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.geom.Rectangle;
   import com.ankamagames.xgaming.font.Verdana;
   import com.ankamagames.xgaming.ui.event.ShowTooltipEvent;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.ankamagames.xgaming.utils.math.geom.Point2;
   import com.reider.log4AS3.ILogger;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.events.TimerEvent;
   import flash.utils.Timer;
   import org.robotlegs.utilities.modular.mvcs.ModuleMediator;
   
   public class TooltipFrameMediator extends ModuleMediator
   {
      
      private static const OFFSET:Point2 = new Point2(0,30);
      
      private static const SHOW_TIME_OUT:int = 300;
      
      private static const LOGGER:ILogger = LoggerFactory.getLogger(TooltipFrameMediator);
      
      private var _view:TooltipFrameView;
      
      private var _lastEvent:ShowTooltipEvent;
      
      private var _timer:Timer;
      
      private var _tooltipView:TooltipView;

      private var _pinned:Boolean;
      
      public function TooltipFrameMediator(param1:TooltipFrameView)
      {
         super();
         this._view = param1;
      }
      
      override public function onRegister() : void
      {
         super.onRegister();
         addModuleListener(ShowTooltipEvent.EVENT,this.showTooltip);
         this._view.stage.addEventListener(MouseEvent.MOUSE_DOWN,this.stageMouseHandler,false,0,true);
         this._view.stage.addEventListener(MouseEvent.MOUSE_UP,this.stageMouseHandler,false,0,true);
      }
      
      override public function onRemove() : void
      {
         super.onRemove();
         this.clear();
         if(this._view.stage != null)
         {
            this._view.stage.removeEventListener(MouseEvent.MOUSE_DOWN,this.stageMouseHandler);
            this._view.stage.removeEventListener(MouseEvent.MOUSE_UP,this.stageMouseHandler);
         }
      }
      
      private function stageMouseHandler(param1:MouseEvent) : void
      {
         // Keep a pinned icon alive through the down/up preceding its next click.
         if(this._pinned && this._lastEvent != null)
         {
            var owner:DisplayObject = this._lastEvent.displayObject;
            var target:DisplayObject = param1.target as DisplayObject;
            if(owner == target || (target != null && owner is DisplayObjectContainer &&
               DisplayObjectContainer(owner).contains(target))) return;
         }
         this.clear();
      }
      
      private function showTooltip(param1:ShowTooltipEvent) : void
      {
         var icon:BaseComponent = param1.displayObject as BaseComponent;
         var tapped:Boolean = icon != null && icon.tapTooltipRequested;
         if(this._pinned && !tapped) return;
         var toggleOff:Boolean = tapped && this._pinned && this._lastEvent != null &&
            this._lastEvent.displayObject == param1.displayObject;
         this.clear();
         if(toggleOff || param1.text == null || param1.text.length == 0) return;
         this._lastEvent = param1;
         this._pinned = tapped;
         this._lastEvent.displayObject.addEventListener(Event.REMOVED_FROM_STAGE, this.sourceRemoved, false, 0, true);
         this._lastEvent.displayObject.addEventListener(BaseComponent.TOOLTIP_CONTENT_CHANGED, this.sourceRemoved, false, 0, true);
         if(tapped)
         {
            this.timerComplete(null);
            return;
         }
         this._lastEvent.displayObject.addEventListener(MouseEvent.ROLL_OUT,this.rollOut,false,0,true);
         this._lastEvent.displayObject.addEventListener(MouseEvent.MOUSE_MOVE,this.mouseMove,false,0,true);
         this._timer = new Timer(SHOW_TIME_OUT,1);
         this._timer.addEventListener(TimerEvent.TIMER_COMPLETE,this.timerComplete,false,0,true);
         this._timer.start();
      }

      private function sourceRemoved(event:Event) : void
      {
         this.clear();
      }

      private function timerComplete(param1:Event) : void
      {
         if(this._tooltipView != null)
         {
            throw IllegalStateError("tooltipView must be null");
         }
         this.clearTimer();
         this._lastEvent.displayObject.removeEventListener(MouseEvent.MOUSE_MOVE,this.mouseMove);
         var _loc2_:Point2 = new Point2(this._view.mouseX,this._view.mouseY);
         if(this._pinned)
         {
            var bounds:Rectangle = this._lastEvent.displayObject.getBounds(this._view);
            _loc2_ = new Point2(bounds.x, bounds.bottom);
         }
         this._tooltipView = new TooltipView();
         this._tooltipView.fontFamily = Verdana.NAME;
         this._tooltipView.setContent(this._lastEvent.text,this._lastEvent.graphicElements);
         this._tooltipView.position = _loc2_.add(OFFSET);
         this._view.addChild(this._tooltipView);
      }
      
      private function rollOut(param1:MouseEvent) : void
      {
         this.clear();
      }
      
      private function mouseMove(param1:MouseEvent) : void
      {
         if(this._timer != null)
         {
            this._timer.reset();
            this._timer.start();
         }
      }
      
      private function clear() : void
      {
         this._pinned = false;
         if(this._lastEvent != null)
         {
            this._lastEvent.displayObject.removeEventListener(Event.REMOVED_FROM_STAGE, this.sourceRemoved);
            this._lastEvent.displayObject.removeEventListener(BaseComponent.TOOLTIP_CONTENT_CHANGED, this.sourceRemoved);
            this._lastEvent.displayObject.removeEventListener(MouseEvent.ROLL_OUT,this.rollOut);
            this._lastEvent.displayObject.removeEventListener(MouseEvent.MOUSE_MOVE,this.mouseMove);
            this._lastEvent = null;
         }
         this.clearTimer();
         if(this._tooltipView != null)
         {
            if(this._tooltipView.parent == this._view)
            {
               this._view.removeChild(this._tooltipView);
            }
            this._tooltipView = null;
         }
         if(this._view.numChildren != 0)
         {
            LOGGER.warn("_view.numChildren should be 0 but was {}",this._view.numChildren);
         }
      }
      
      private function clearTimer() : void
      {
         if(this._timer != null)
         {
            this._timer.removeEventListener(TimerEvent.TIMER_COMPLETE,this.timerComplete);
            this._timer.reset();
            this._timer = null;
         }
      }
   }
}

