package com.ankamagames.boufbowl.client.match.strategic.view.field
{
   import com.ankamagames.boufbowl.client.application.IColorScheme;
   import com.ankamagames.boufbowl.client.application.dragndrop.DragNDropEvent;
   import com.ankamagames.boufbowl.client.application.dragndrop.DragNDropperMediator;
   import com.ankamagames.boufbowl.client.application.event.BoufbowlerClickedEvent;
   import com.ankamagames.boufbowl.client.application.mediator.BoufbowlMediator;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.match.strategic.controller.SelectActiveBoufbowlerCommand;
   import com.ankamagames.boufbowl.client.match.controller.PhaseEndCommand;
   import com.ankamagames.boufbowl.client.match.strategic.event.StartDragEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.ActiveBoufbowlerChangedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufballAddedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufbowlerAddedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufbowlerOrderUpdatedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BringDirectionArrowToFrontEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.FieldModelEvent;
   import com.ankamagames.boufbowl.client.match.strategic.model.FieldModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.Rules;
   import com.ankamagames.boufbowl.client.match.strategic.model.grid.GridModel;
   import com.ankamagames.boufbowl.client.match.strategic.view.GridViewCoordConverter;
   import com.ankamagames.boufbowl.client.match.strategic.view.field.boufball.BoufballFieldRepresentationView;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.netease.protobuf.Int64;
   import flash.events.MouseEvent;
   import flash.events.Event;

   public class FieldMediator extends BoufbowlMediator
   {

      private var _view:FieldView;

      private var _model:FieldModel;

      private var _grid:GridModel;

      private var _fieldViewFactory:FieldViewFactory;

      private var _selectedBoufbowlerId:Int64;

      private var _rules:Rules;

      private var _gridViewCoordConverter:GridViewCoordConverter;

      private var _colorScheme:IColorScheme;

      private var _translator:ITranslator;

      private var _selectingPass:Boolean = false;

      public function FieldMediator(param1:FieldView, param2:FieldModel, param3:GridModel, param4:FieldViewFactory, param5:Rules, param6:GridViewCoordConverter, param7:IColorScheme, param8:ITranslator)
      {
         super();
         this._view = param1;
         this._model = param2;
         this._grid = param3;
         this._fieldViewFactory = param4;
         this._rules = param5;
         this._gridViewCoordConverter = param6;
         this._colorScheme = param7;
         this._translator = param8;
      }

      override public function onRegister() : void
      {
         super.onRegister();
         addContextListener(BoufballAddedEvent.EVENT,this.boufballAdded);
         addContextListener(BoufbowlerAddedEvent.EVENT,this.boufbowlerAdded);
         addContextListener(FieldModel.DISPLAY_PLACEMENT_ZONES_CHANGED,this.fieldDisplayPlacementZonesChanged);
         addContextListener(ActiveBoufbowlerChangedEvent.EVENT,this.activeBoufbowlerChanged);
         addContextListener(BoufbowlerOrderUpdatedEvent.EVENT,this.boufbowlerOrderUpdated);
         addContextListener(DragNDropperMediator.BOUFBOWLER,this.boufbowlerDnd);
         addContextListener(StartDragEvent.STARTED,this.dragStarted);
         addContextListener(DragNDropperMediator.PASS,this.passDnd);
         addContextListener(PhaseEndCommand.STOP_DND,this.clearPassRange);
         addContextListener(BringDirectionArrowToFrontEvent.EVENT,this.bringDirectionArrowToFront);
         addContextListener(FieldModel.BLINKING_CELL_CHANGED,this.blinkingCellChanged);
         addViewListener(MouseEvent.CLICK,this.backgroundLayerClicked);
      }

      private function boufballAdded(param1:BoufballAddedEvent) : void
      {
         var _loc2_:BoufballFieldRepresentationView = new BoufballFieldRepresentationView();
         this._view.addBoufball(_loc2_);
      }

      private function boufbowlerAdded(param1:BoufbowlerAddedEvent) : void
      {
         this._view.addBoufbowler(this._fieldViewFactory.getBoufbowlerFieldRepresentationView(param1.boufbowler));
         this._view.addArrows(this._fieldViewFactory.getDirectionArrowSpriteView(param1.boufbowler),this._fieldViewFactory.getPassArrowSpriteView(param1.boufbowler),param1.boufbowler.onPlayerSide);
         this._view.addClassOrderIndicator(this._fieldViewFactory.getClassOrderIndicatorView(param1.boufbowler),param1.boufbowler.onPlayerSide);
      }

      private function fieldDisplayPlacementZonesChanged(param1:FieldModelEvent) : void
      {
         if(param1.field.displayPlacementZones)
         {
            this._view.displayPlacementZones(param1.field.placementZones);
         }
         else
         {
            this._view.clearPlacementZones(param1.field.placementZones);
         }
      }

      private function activeBoufbowlerChanged(param1:ActiveBoufbowlerChangedEvent) : void
      {
         this._selectingPass = false;
         this._selectedBoufbowlerId = param1.activeBoufbowler == null ? null : param1.activeBoufbowler.id;
         this.updateGridReferenceDistancesColors(param1.activeBoufbowler);
      }

      private function boufbowlerOrderUpdated(param1:BoufbowlerOrderUpdatedEvent) : void
      {
         if(param1.boufbowler.id.equals(this._selectedBoufbowlerId))
         {
            this.updateGridReferenceDistancesColors(param1.boufbowler);
         }
      }

      private function boufbowlerDnd(param1:DragNDropEvent) : void
      {
         if(!param1.drop)
         {
            this._view.highlightedCell = this._gridViewCoordConverter.gridPointFromLogicalPoint(param1.point);
         }
         else
         {
            this._view.highlightedCell = null;
         }
      }

      private function dragStarted(event:StartDragEvent) : void
      {
         this._selectingPass = event.attachedData.eventTypeToDispatch == DragNDropperMediator.PASS;
         this.updateGridReferenceDistancesColors(this._model.activeBoufbowler);
      }

      private function passDnd(event:DragNDropEvent) : void
      {
         if(event.drop) this.clearPassRange(event);
      }

      private function clearPassRange(event:Event) : void
      {
         this._selectingPass = false;
         this._view.clearPassRangeOutline();
      }

      private function bringDirectionArrowToFront(param1:BringDirectionArrowToFrontEvent) : void
      {
         this._view.bringDirectionArrowToFront(param1.directionArrow);
      }

      private function blinkingCellChanged(param1:FieldModelEvent) : void
      {
         this._view.blinkingCell = param1.field.blinkingCell;
      }

      private function backgroundLayerClicked(param1:MouseEvent) : void
      {
         if(param1.target == this._view.cellsLayer)
         {
            dispatch(new BoufbowlerClickedEvent(SelectActiveBoufbowlerCommand.BOUFBOWLER_CLICKED,null));
            playSound(InterfaceSoundEvents.BOUFBOWLER_UNSELECT);
         }
      }

      private function updateGridReferenceDistancesColors(param1:IBoufbowlerInMatchModel) : void
      {
         this._view.clearPassRangeOutline();
         var _loc2_:Number = NaN;
         var _loc3_:Number = NaN;
         if(param1 == null)
         {
            this._view.clearGridReferenceDistancesColors(this._grid);
         }
         else
         {
            _loc2_ = this._rules.getReferenceDistance(param1.order.elements);
            _loc3_ = this._rules.getMaxDistance(_loc2_);
            this._view.setGridReferenceDistancesColors(this._grid,param1.position,_loc2_,_loc3_);
            if(this._selectingPass && this._rules.canPassBall(param1.order) && !param1.order.classOrderActivated)
               this._view.setPassRangeOutline(this._grid,param1.position,this._rules.getMaxPassDistance(param1.order.elements));
         }
      }
   }
}
