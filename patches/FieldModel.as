package com.ankamagames.boufbowl.client.match.strategic.model
{
   import as3.collections.ILinkedList;
   import as3.collections.IList;
   import as3.collections.IMap;
   import as3.collections.LinkedList;
   import as3.collections.iterators.IIterator;
   import as3.collections.iterators.IMapIterator;
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.match.model.OrderModel;
   import com.ankamagames.boufbowl.client.match.strategic.event.ActiveBoufbowlerChangedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufballAddedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufballUpdatedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufbowlerAddedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufbowlerOrderUpdatedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufbowlerUpdatedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.FieldModelEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.TargetSelectionRequestEvent;
   import com.ankamagames.boufbowl.protocol.BoufbowlerClass;
   import com.ankamagames.boufbowl.protocol.BoufbowlerStatus;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.netease.protobuf.Int64;
   import flash.errors.IllegalOperationError;
   import org.robotlegs.utilities.modular.mvcs.ModuleActor;
   
   public class FieldModel extends ModuleActor
   {
      
      public static const DISPLAY_PLACEMENT_ZONES_CHANGED:String = "com.ankamagames.boufbowl.client.match.strategic.model.FieldModel.DISPLAY_PLACEMENT_ZONES_CHANGED";
      
      public static const BLINKING_CELL_CHANGED:String = "com.ankamagames.boufbowl.client.match.strategic.model.FieldModel.BLINKING_CELL_CHANGED";
      
      public static const ZOBAL_MASK_SELECTION_REQUEST:String = "com.ankamagames.boufbowl.client.match.strategic.model.FieldModel.ZOBAL_MASK_SELECTION_REQUEST";
      
      private var _rules:Rules;
      
      private var _side:int;
      
      private var _placementBoufballSide:int;
      
      private var _boufball:IBoufballModel;
      
      private var _boufbowlers:ILinkedList;
      
      private var _placementZones:IMap;
      
      private var _displayPlacementZones:Boolean;
      
      private var _activeBoufbowler:IBoufbowlerInMatchModel;
      
      private var _classOrderBoufbowler:IBoufbowlerInMatchModel;
      
      private var _blinkingCell:HexPoint;
      
      public function FieldModel(param1:Rules)
      {
         super();
         this._rules = param1;
      }
      
      public function get side() : int
      {
         return this._side;
      }
      
      public function get opponentSide() : int
      {
         return this._side == Side.LEFT ? Side.RIGHT : Side.LEFT;
      }
      
      public function get placementBoufballSide() : int
      {
         return this._placementBoufballSide;
      }
      
      public function set placementBoufballSide(param1:int) : void
      {
         this._placementBoufballSide = param1;
      }
      
      public function get boufball() : IBoufballModel
      {
         return this._boufball;
      }
      
      public function get allBoufbowlers() : IList
      {
         return this._boufbowlers;
      }
      
      public function get boufbowlersOnField() : IList
      {
         var _loc2_:IBoufbowlerInMatchModel = null;
         var _loc1_:IList = new LinkedList();
         var _loc3_:IIterator = this.allBoufbowlers.getIterator();
         while(_loc3_.hasNext())
         {
            _loc2_ = _loc3_.getNext();
            if(_loc2_.onField)
            {
               _loc1_.addItem(_loc2_);
            }
         }
         return _loc1_;
      }
      
      public function get placementZones() : IMap
      {
         return this._placementZones;
      }
      
      public function get displayPlacementZones() : Boolean
      {
         return this._displayPlacementZones;
      }
      
      public function set displayPlacementZones(param1:Boolean) : void
      {
         if(this._displayPlacementZones == param1)
         {
            return;
         }
         this._displayPlacementZones = param1;
         dispatch(new FieldModelEvent(DISPLAY_PLACEMENT_ZONES_CHANGED,this));
      }
      
      public function get activeBoufbowler() : IBoufbowlerInMatchModel
      {
         return this._activeBoufbowler;
      }
      
      public function set activeBoufbowler(param1:IBoufbowlerInMatchModel) : void
      {
         if(this._activeBoufbowler == param1)
         {
            return;
         }
         if(param1 != null && param1.side != this.side)
         {
            return;
         }
         var _loc2_:IBoufbowlerInMatchModel = this._activeBoufbowler;
         this._activeBoufbowler = param1;
         dispatch(new ActiveBoufbowlerChangedEvent(this._activeBoufbowler,_loc2_));
      }
      
      public function get blinkingCell() : HexPoint
      {
         return this._blinkingCell;
      }
      
      public function set blinkingCell(param1:HexPoint) : void
      {
         if(this._blinkingCell == null && param1 == null)
         {
            return;
         }
         if(this._blinkingCell != null && param1 != null && this._blinkingCell.equals(param1))
         {
            return;
         }
         this._blinkingCell = param1;
         dispatch(new FieldModelEvent(BLINKING_CELL_CHANGED,this));
      }
      
      public function getFirstBoufbowlerOnField(param1:int) : Int64
      {
         var _loc2_:IBoufbowlerInMatchModel = null;
         var _loc3_:IIterator = this.allBoufbowlers.getIterator();
         while(_loc3_.hasNext())
         {
            _loc2_ = _loc3_.getNext();
            if(_loc2_.onField && _loc2_.side == param1)
            {
               return _loc2_.id;
            }
         }
         return null;
      }
      
      public function getBoufbowlerBySide(param1:int) : ILinkedList
      {
         var _loc4_:IBoufbowlerInMatchModel = null;
         var _loc2_:ILinkedList = new LinkedList();
         var _loc3_:IIterator = this._boufbowlers.getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            if(_loc4_.side == param1)
            {
               _loc2_.addItem(_loc4_);
            }
         }
         return _loc2_;
      }
      
      public function getSideCaptain(param1:int) : IBoufbowlerInMatchModel
      {
         var _loc4_:IBoufbowlerInMatchModel = null;
         var _loc2_:uint = 0;
         var _loc3_:IIterator = this.getBoufbowlerBySide(param1).getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            if(++_loc2_ == 8)
            {
               return _loc4_;
            }
         }
         throw new IllegalOperationError("We should have at least 8 boufbowlers.");
      }
      
      public function setup(param1:int, param2:IBoufballModel, param3:ILinkedList, param4:IMap) : void
      {
         if(this._boufbowlers != null)
         {
            throw new IllegalStateError("Can\'t init the match twice");
         }
         this._side = param1;
         this._boufball = param2;
         this._boufbowlers = param3;
         this._placementZones = param4;
         dispatch(new BoufballAddedEvent(this._boufball));
         this.prepareBoufbowlers();
         var _loc5_:IIterator = this._boufbowlers.getIterator();
         while(_loc5_.hasNext())
         {
            dispatch(new BoufbowlerAddedEvent(_loc5_.getNext()));
         }
      }
      
      public function resetBoufbowlersOrder() : void
      {
         this.activeBoufbowler = null;
         this._classOrderBoufbowler = null;
         this.prepareBoufbowlers();
      }
      
      public function getPlacementZoneType(param1:HexPoint) : Number
      {
         if(param1 == null) return -1;
         var zones:IMapIterator = this._placementZones.getMapIterator();
         while(zones.hasNext())
         {
            var cells:Array = zones.getNext();
            var kind:int = zones.getKey();
            for each(var cell:HexPoint in cells)
            {
               if(param1.equals(cell)) return kind;
            }
         }
         return -1;
      }
      
      public function getBoufbowlerInPlacementZone(param1:int) : IBoufbowlerInMatchModel
      {
         var _loc3_:HexPoint = null;
         var _loc4_:IIterator = null;
         var _loc5_:IBoufbowlerInMatchModel = null;
         var _loc2_:Array = this._placementZones.getItem(param1);
         loop0:
         for each(_loc3_ in _loc2_)
         {
            _loc4_ = this._boufbowlers.getIterator();
            do
            {
               if(!_loc4_.hasNext())
               {
                  continue loop0;
               }
            }
            while(_loc5_ = _loc4_.getNext(), !_loc5_.position.equals(_loc3_));
            return _loc5_;
         }
         return null;
      }
      
      public function getBoufbowler(param1:Int64) : IBoufbowlerInMatchModel
      {
         var _loc3_:IBoufbowlerInMatchModel = null;
         var _loc2_:IIterator = this._boufbowlers.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(_loc3_.id.equals(param1))
            {
               return _loc3_;
            }
         }
         return null;
      }
      
      public function getOwnBoufbowlerAt(param1:HexPoint) : IBoufbowlerInMatchModel
      {
         var _loc3_:IBoufbowlerInMatchModel = null;
         var _loc2_:IIterator = this._boufbowlers.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(_loc3_.position.equals(param1) && _loc3_.side == this._side)
            {
               return _loc3_;
            }
         }
         return null;
      }
      
      public function getActiveBoufbowlerTargetAt(param1:HexPoint) : IBoufbowlerInMatchModel
      {
         var _loc3_:IBoufbowlerInMatchModel = null;
         var _loc2_:IIterator = this._boufbowlers.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(_loc3_.position.equals(param1) && _loc3_ != this._activeBoufbowler && _loc3_.onField)
            {
               return _loc3_;
            }
         }
         return null;
      }
      
      public function setBoufbowlerElement(param1:uint, param2:int) : void
      {
         var _loc3_:OrderModel = this._activeBoufbowler.order;
         if(_loc3_.classOrderActivated)
         {
            return;
         }
         if(_loc3_.emptyOrder)
         {
            _loc3_.targetCell = this._activeBoufbowler.position;
            _loc3_.fillWithElement(param2);
         }
         else
         {
            _loc3_.setElement(param1,param2);
         }
         if(_loc3_.passTarget != null && !this._rules.canPassBall(_loc3_))
         {
            _loc3_.passTarget = null;
         }
         dispatch(new BoufbowlerOrderUpdatedEvent(this._activeBoufbowler));
      }
      
      public function toggleBoufbowlerClassOrder() : void
      {
         var _loc1_:OrderModel = this._activeBoufbowler.order;
         if(!_loc1_.classOrderActivated)
         {
            if(this._activeBoufbowler.attributes.classOrders >= 1 && this._activeBoufbowler.status != BoufbowlerStatus.KO)
            {
               if(this._activeBoufbowler.boufbowlerClass == BoufbowlerClass.ZOBAL)
               {
                  dispatch(new FieldModelEvent(ZOBAL_MASK_SELECTION_REQUEST,this));
               }
               else
               {
                  this.activateClassOrder();
               }
            }
         }
         else
         {
            _loc1_.classOrderActivated = false;
            _loc1_.zobalMask = NaN;
            this._classOrderBoufbowler = null;
            dispatch(new BoufbowlerOrderUpdatedEvent(this._activeBoufbowler));
         }
      }
      
      public function setBoufbowlerZobalMaskOrder(param1:int) : void
      {
         this.activateClassOrder(param1);
      }
      
      public function setBoufbowlerTargetCell(param1:HexPoint) : void
      {
         if(this._activeBoufbowler != null && this._activeBoufbowler.order.classOrderActivated) return;
         var _loc2_:OrderModel = this._activeBoufbowler.order;
         _loc2_.targetCell = param1;
         this.changeBoufbowlerTargetToBoufbowler();
         dispatch(new BoufbowlerOrderUpdatedEvent(this._activeBoufbowler));
      }
      
      public function changeBoufbowlerTargetToCell() : void
      {
         if(this._activeBoufbowler != null && this._activeBoufbowler.order.classOrderActivated) return;
         if(this._activeBoufbowler == null)
         {
            return;
         }
         var _loc1_:OrderModel = this._activeBoufbowler.order;
         if(_loc1_.targetType == OrderModel.TARGETING_PLAYER)
         {
            _loc1_.targetCell = _loc1_.targetBoufbowler.position;
         }
         dispatch(new BoufbowlerOrderUpdatedEvent(this._activeBoufbowler));
      }
      
      public function setBoufbowlerPassTarget(param1:IBoufbowlerInMatchModel) : void
      {
         if(this._activeBoufbowler != null && this._activeBoufbowler.order.classOrderActivated) return;
         var _loc2_:OrderModel = this._activeBoufbowler.order;
         _loc2_.passTarget = param1;
         dispatch(new BoufbowlerOrderUpdatedEvent(this._activeBoufbowler));
      }
      
      public function update() : void
      {
         var _loc2_:IBoufbowlerInMatchModel = null;
         dispatch(new BoufballUpdatedEvent(this._boufball));
         var _loc1_:IIterator = this._boufbowlers.getIterator();
         while(_loc1_.hasNext())
         {
            _loc2_ = _loc1_.getNext();
            dispatch(new BoufbowlerUpdatedEvent(_loc2_));
            dispatch(new BoufbowlerOrderUpdatedEvent(_loc2_));
         }
      }
      
      internal function get classOrderBoufbowler() : IBoufbowlerInMatchModel
      {
         return this._classOrderBoufbowler;
      }
      
      private function activateClassOrder(param1:Number = 0) : void
      {
         if(param1 == 0) param1 = NaN;
         var _loc2_:OrderModel = this._activeBoufbowler.order;
         if(!isNaN(param1) && this._activeBoufbowler.currentZobalMask == param1)
         {
            return;
         }
         if(this._classOrderBoufbowler != null)
         {
            this._classOrderBoufbowler.order.resetToEmptyOrder();
            dispatch(new BoufbowlerOrderUpdatedEvent(this._classOrderBoufbowler));
         }
         _loc2_.resetToEmptyOrder();
         _loc2_.classOrderActivated = true;
         if(!isNaN(param1))
         {
            _loc2_.zobalMask = param1;
         }
         this._classOrderBoufbowler = this._activeBoufbowler;
         dispatch(new BoufbowlerOrderUpdatedEvent(this._activeBoufbowler));
      }
      
      private function prepareBoufbowlers() : void
      {
         var _loc2_:IBoufbowlerInMatchModel = null;
         var _loc1_:IIterator = this._boufbowlers.getIterator();
         while(_loc1_.hasNext())
         {
            _loc2_ = _loc1_.getNext();
            _loc2_.onPlayerSide = _loc2_.side == this.side;
            _loc2_.resetOrder();
         }
      }
      
      private function changeBoufbowlerTargetToBoufbowler() : void
      {
         if(this._activeBoufbowler == null)
         {
            return;
         }
         var _loc1_:IBoufbowlerInMatchModel = this.getActiveBoufbowlerTargetAt(this._activeBoufbowler.order.targetCell);
         if(_loc1_ == null)
         {
            dispatchToModules(new InterfaceSoundEvent(InterfaceSoundEvents.DROP_MOVE_ARROW_ON_EMPTY_CASE));
            return;
         }
         if(_loc1_ == this.activeBoufbowler)
         {
            return;
         }
         dispatchToModules(new InterfaceSoundEvent(InterfaceSoundEvents.DROP_MOVE_ARROW_ON_OCCUPED_CASE));
         if(this._activeBoufbowler.order.classOrderActivated) return;
         this._activeBoufbowler.order.targetBoufbowler = _loc1_;
         dispatch(new TargetSelectionRequestEvent(this._activeBoufbowler.position,_loc1_.position,true,true));
      }
   }
}

