package com.ankamagames.boufbowl.client.match.strategic.view.field
{
   import flash.system.Capabilities;
   import as3.collections.IMap;
   import as3.collections.LinkedMap;
   import as3.collections.iterators.IIterator;
   import as3.collections.iterators.IMapIterator;
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.client.application.dragndrop.DragNDropperView;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.IMatchColorScheme;
   import com.ankamagames.boufbowl.client.match.strategic.model.grid.CellModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.grid.GridModel;
   import com.ankamagames.boufbowl.client.match.strategic.view.GridViewCoordConverter;
   import com.ankamagames.boufbowl.client.match.strategic.view.field.arrow.DirectionArrowSpriteView;
   import com.ankamagames.boufbowl.client.match.strategic.view.field.arrow.PassArrowSpriteView;
   import com.ankamagames.boufbowl.client.match.strategic.view.field.boufball.BoufballFieldRepresentationView;
   import com.ankamagames.boufbowl.client.match.strategic.view.field.boufbowler.BoufbowlerFieldRepresentationView;
   import com.ankamagames.boufbowl.client.match.strategic.view.field.indicator.ClassOrderIndicatorView;
   import com.ankamagames.boufbowl.match.strategic.field.FieldSprite;
   import com.ankamagames.boufbowl.match.strategic.field.OpponentArrowsLayer;
   import com.ankamagames.xgaming.utils.display.DisplayListUtils;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.ankamagames.xgaming.utils.math.geom.Point2;
   import flash.display.DisplayObjectContainer;
   import flash.display.Sprite;

   public class FieldView extends FieldSprite
   {

      private var _orderPanel:OrderPanelView;

      private var _dragNDropper:DragNDropperView;

      private var _targetSelector:TargetSelectorSpriteView;

      private var _gridViewCoordConverter:GridViewCoordConverter;

      private var _translator:ITranslator;

      private var _colorScheme:IMatchColorScheme;

      private var _cellsMap:IMap;

      private var _cellsLayer:Sprite;

      private var _boufbowlersLayer:Sprite;

      private var _ballLayer:Sprite;

      private var _directionArrowsLayer:Sprite;

      private var _passArrowsLayer:Sprite;

      private var _orderPanelLayer:Sprite;

      private var _targetSelectorLayer:Sprite;

      private var _opponentArrowsLayer:OpponentArrowsLayer;

      private var _opponentClassOrderIndicatorLayer:Sprite;

      private var _highlightedCell:CellSpriteView;

      private var _blinkingCell:CellSpriteView;

      public function FieldView(param1:GridModel, param2:OrderPanelView, param3:DragNDropperView, param4:TargetSelectorSpriteView, param5:GridViewCoordConverter, param6:ITranslator, param7:IMatchColorScheme)
      {
         super();
         this._orderPanel = param2;
         this._dragNDropper = param3;
         this._targetSelector = param4;
         this._gridViewCoordConverter = param5;
         this._translator = param6;
         this._colorScheme = param7;
         this.init(param1);
      }

      public function get cellsLayer() : Sprite
      {
         return this._cellsLayer;
      }

      public function set highlightedCell(param1:HexPoint) : void
      {
         if(this._highlightedCell != null)
         {
            this._highlightedCell.highlighted = false;
            this._highlightedCell = null;
         }
         if(param1 == null || !this.hasCell(param1))
         {
            return;
         }
         this._highlightedCell = this.getCell(param1);
         this._highlightedCell.highlighted = true;
      }

      public function set blinkingCell(param1:HexPoint) : void
      {
         if(this._blinkingCell != null)
         {
            this._blinkingCell.blinking = false;
            this._blinkingCell = null;
         }
         if(param1 == null || !this.hasCell(param1))
         {
            return;
         }
         this._blinkingCell = this.getCell(param1);
         this._blinkingCell.blinking = true;
      }

      public function hasCell(param1:HexPoint) : Boolean
      {
         return this._cellsMap.hasKey(param1.toInt());
      }

      public function getCell(param1:HexPoint) : CellSpriteView
      {
         if(!this.hasCell(param1))
         {
            throw new IllegalStateError("La case (" + param1.toString() + ") n\'existe pas !");
         }
         return this._cellsMap.getItem(param1.toInt());
      }

      public function addBoufball(param1:BoufballFieldRepresentationView) : void
      {
         this._ballLayer.addChild(param1);
      }

      public function addBoufbowler(param1:BoufbowlerFieldRepresentationView) : void
      {
         this._boufbowlersLayer.addChild(param1);
      }

      public function addClassOrderIndicator(param1:ClassOrderIndicatorView, param2:Boolean) : void
      {
         if(!param2)
         {
            this._opponentClassOrderIndicatorLayer.addChild(param1);
         }
      }

      public function addArrows(param1:DirectionArrowSpriteView, param2:PassArrowSpriteView, param3:Boolean) : void
      {
         if(param3)
         {
            this._directionArrowsLayer.addChild(param1);
            this._passArrowsLayer.addChild(param2);
         }
         else
         {
            DisplayObjectContainer(this._opponentArrowsLayer.animated["direction"]).addChild(param1);
            DisplayObjectContainer(this._opponentArrowsLayer.animated["pass"]).addChild(param2);
         }
      }

      public function bringDirectionArrowToFront(param1:DirectionArrowSpriteView) : void
      {
         DisplayListUtils.bringToFront(param1);
      }

      public function showOpponentLayer() : void
      {
         this._opponentArrowsLayer.visible = true;
         this._opponentArrowsLayer.gotoAndPlay(1);
         this._opponentClassOrderIndicatorLayer.visible = true;
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.OPPONENT_ARROWS_DISPLAY));
      }

      public function hideOpponentLayer() : void
      {
         this._opponentArrowsLayer.visible = false;
         this._opponentClassOrderIndicatorLayer.visible = false;
      }

      public function displayPlacementZones(param1:IMap) : void
      {
         var _loc3_:Array = null;
         var _loc4_:int = 0;
         var _loc5_:uint = 0;
         var _loc6_:Number = NaN;
         var _loc7_:HexPoint = null;
         var _loc8_:CellSpriteView = null;
         var _loc2_:IMapIterator = param1.getMapIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            _loc4_ = _loc2_.getKey();
            _loc5_ = this._colorScheme.getPlacementZoneColor(_loc4_);
            _loc6_ = this._colorScheme.getPlacementZoneAlpha(_loc4_);
            for each(_loc7_ in _loc3_)
            {
               _loc8_ = this.getCell(_loc7_);
               _loc8_.cellShape.color = _loc5_;
               _loc8_.cellShape.alpha = _loc6_;
            }
         }
      }

      public function clearPlacementZones(param1:IMap) : void
      {
         var _loc3_:Array = null;
         var _loc4_:HexPoint = null;
         var _loc5_:CellSpriteView = null;
         var _loc2_:IMapIterator = param1.getMapIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            for each(_loc4_ in _loc3_)
            {
               _loc5_ = this.getCell(_loc4_);
               _loc5_.cellShape.alpha = 0;
            }
         }
      }

      public function setGridReferenceDistancesColors(param1:GridModel, param2:HexPoint, param3:Number, param4:Number) : void
      {
         var _loc6_:CellModel = null;
         var _loc7_:CellSpriteView = null;
         var _loc8_:Number = NaN;
         var _loc9_:Number = NaN;
         var _loc5_:IIterator = param1.getCellsIterator();
         while(_loc5_.hasNext())
         {
            _loc6_ = _loc5_.getNext();
            _loc7_ = this.getCell(_loc6_.position);
            _loc8_ = param2.getDistance(_loc6_.position);
            if(_loc8_ <= param3)
            {
               _loc7_.cellShape.color = this._colorScheme.safeZoneCellColor;
               _loc7_.cellShape.alpha = this._colorScheme.safeZoneCellAlpha;
               _loc7_.setTooltip(null);
            }
            else if(_loc8_ <= param4)
            {
               _loc9_ = (_loc8_ - param3) / (param4 - param3);
               _loc7_.cellShape.color = this._colorScheme.getRiskyZoneCellColor(_loc9_);
               _loc7_.cellShape.alpha = this._colorScheme.getRiskyZoneCellAlpha(_loc9_);
               _loc7_.setTooltip(this._translator.getText(LangConstants.FIELD_MOVEMENT_DANGER_TOOLTIP));
            }
            else
            {
               _loc7_.cellShape.color = this._colorScheme.forbiddenZoneCellColor;
               _loc7_.cellShape.alpha = this._colorScheme.forbiddenZoneCellAlpha;
               _loc7_.setTooltip(null);
            }
         }
      }

      public function clearGridReferenceDistancesColors(param1:GridModel) : void
      {
         var _loc3_:CellModel = null;
         var _loc2_:IIterator = param1.getCellsIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            this.getCell(_loc3_.position).cellShape.alpha = 0;
         }
      }

      private function init(param1:GridModel) : void
      {
         this.initLayers();
         this.initCells(param1);
         this._orderPanel.visible = false;
         this._orderPanelLayer.addChild(this._orderPanel);
         this._targetSelector.visible = false;
         this._targetSelectorLayer.addChild(this._targetSelector);
         addChild(this._dragNDropper);
      }

      private function initLayers() : void
      {
         this._cellsLayer = new Sprite();
         this._cellsLayer.mouseChildren = false;
         // Cache the complete grid in browser runtimes; child changes invalidate it.
         this._cellsLayer.cacheAsBitmap = Capabilities.playerType == "PlugIn";
         this._boufbowlersLayer = new Sprite();
         this._boufbowlersLayer.mouseEnabled = false;
         this._ballLayer = new Sprite();
         this._ballLayer.mouseEnabled = false;
         this._ballLayer.mouseChildren = false;
         this._directionArrowsLayer = new Sprite();
         this._directionArrowsLayer.mouseEnabled = false;
         this._directionArrowsLayer.mouseChildren = false;
         this._passArrowsLayer = new Sprite();
         this._passArrowsLayer.mouseEnabled = false;
         this._passArrowsLayer.mouseChildren = false;
         this._orderPanelLayer = new Sprite();
         this._orderPanelLayer.mouseEnabled = false;
         this._targetSelectorLayer = new Sprite();
         this._targetSelectorLayer.mouseEnabled = false;
         this._opponentArrowsLayer = new OpponentArrowsLayer();
         this._opponentArrowsLayer.visible = false;
         this._opponentArrowsLayer.mouseEnabled = false;
         this._opponentArrowsLayer.animated.cacheAsBitmap = true;
         this._opponentClassOrderIndicatorLayer = new Sprite();
         this._opponentClassOrderIndicatorLayer.visible = false;
         this._opponentClassOrderIndicatorLayer.mouseEnabled = false;
         addChild(this._cellsLayer);
         addChild(this._boufbowlersLayer);
         addChild(this._ballLayer);
         addChild(this._directionArrowsLayer);
         addChild(this._passArrowsLayer);
         addChild(this._orderPanelLayer);
         addChild(this._targetSelectorLayer);
         addChild(this._opponentArrowsLayer);
         addChild(this._opponentClassOrderIndicatorLayer);
      }

      private function initCells(param1:GridModel) : void
      {
         var _loc3_:CellModel = null;
         var _loc4_:CellSpriteView = null;
         var _loc5_:Point2 = null;
         this._cellsMap = new LinkedMap();
         var _loc2_:IIterator = param1.getCellsIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            _loc4_ = new CellSpriteView(_loc3_,this._colorScheme);
            _loc4_.cacheAsBitmap = true;
            _loc5_ = this._gridViewCoordConverter.viewPointFromGridPoint(_loc3_.position);
            _loc4_.x = _loc5_.x;
            _loc4_.y = _loc5_.y;
            this._cellsMap.addItem(_loc4_.model.position.toInt(),_loc4_);
            this._cellsLayer.addChild(_loc4_);
         }
      }
   }
}
