package com.ankamagames.boufbowl.client.match.strategic.controller
{
   import com.ankamagames.boufbowl.client.application.dragndrop.DragNDropEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.match.model.MatchModel;
   import com.ankamagames.boufbowl.client.match.model.MatchState;
   import com.ankamagames.boufbowl.client.match.strategic.event.DragNDropUpdateViewEvent;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.LinkedBoufbowlerData;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.protocol.BoufballStatus;
   import com.ankamagames.boufbowl.protocol.PlacementZoneType;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class PlacementDragNDropCommand extends ModuleCommand
   {
      
      public static const PLACEMENT:String = "com.ankamagames.boufbowl.client.match.strategic.controller.PlacementDragNDropCommand.PLACEMENT";
      
      private var _event:DragNDropEvent;
      
      private var _match:MatchModel;
      
      public function PlacementDragNDropCommand(param1:MatchModel, param2:DragNDropEvent)
      {
         super();
         this._match = param1;
         this._event = param2;
      }
      
      override public function execute() : void
      {
         if(this._match.state != MatchState.PLACEMENT_PHASE)
         {
            return;
         }
         this.proceed();
      }
      
      private function proceed() : void
      {
         var _loc3_:Number = NaN;
         var _loc4_:IBoufbowlerInMatchModel = null;
         var _loc1_:HexPoint = this._match.grid.gridPoint(this._event.point);
         var _loc2_:IBoufbowlerInMatchModel = this._match.field.getBoufbowler(LinkedBoufbowlerData(this._event.attachedData).boufbowlerId);
         if(!this._event.drop)
         {
            dispatch(new DragNDropUpdateViewEvent(PLACEMENT,this._event.point,_loc2_.id,this._match.grid.spacePoint(_loc2_.position)));
            this._match.field.blinkingCell = _loc2_.position;
         }
         else
         {
            _loc3_ = this._match.field.getPlacementZoneType(_loc1_);
            if(_loc3_ != -1)
            {
               _loc4_ = this._match.field.getBoufbowlerInPlacementZone(_loc3_);
               if(_loc4_ != null)
               {
                  dispatchToModules(new InterfaceSoundEvent(InterfaceSoundEvents.PLACEMENT_BOUFBOWLER_DROPPED_ONOCCUPEDZONE));
                  this.moveBoufbowler(_loc4_,_loc2_.position);
               }
               else
               {
                  dispatchToModules(new InterfaceSoundEvent(InterfaceSoundEvents.PLACEMENT_BOUFBOWLER_DROPPED));
               }
               this.moveBoufbowler(_loc2_,_loc1_);
            }
            this.updatePlacementBall();
            this._match.field.blinkingCell = null;
            this._match.field.update();
         }
      }
      
      private function moveBoufbowler(param1:IBoufbowlerInMatchModel, param2:HexPoint) : void
      {
         param1.position = param2;
      }

      private function updatePlacementBall() : void
      {
         var receivingSide:int = this._match.field.placementBoufballSide;
         if(receivingSide != Side.LEFT && receivingSide != Side.RIGHT) return;
         var players:IIterator = this._match.field.allBoufbowlers.getIterator();
         while(players.hasNext()) IBoufbowlerInMatchModel(players.getNext()).hasBall = false;
         var receiver:IBoufbowlerInMatchModel = receivingSide == this._match.field.side
            ? this._match.field.getBoufbowlerInPlacementZone(PlacementZoneType.CENTER) : null;
         if(receiver != null)
         {
            receiver.hasBall = true;
            this._match.field.boufball.status = BoufballStatus.HELD;
            this._match.field.boufball.position = receiver.position;
         }
         else
         {
            this._match.field.boufball.status = BoufballStatus.OUT_OF_BOUNDS;
            this._match.field.boufball.position = null;
         }
      }
   }
}
