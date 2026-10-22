package com.ankamagames.boufbowl.client.match.resolution.builder
{
   import as3.collections.ISortedList;
   import as3.collections.core.SortedArray;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.protocol.InteractionDetails;
   import com.ankamagames.boufbowl.protocol.InteractionEntry;
   import com.ankamagames.boufbowl.protocol.InteractionType;
   import com.ankamagames.boufbowl.protocol.ParticipantDetails;
   import com.ankamagames.boufbowl.protocol.ResolutionScenarioMessage;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;

   internal class BoufballTrackBuilder
   {

      public function BoufballTrackBuilder()
      {
         super();
      }

      public function build(param1:ResolutionScenarioMessage, param2:HexPoint, param3:CommonData) : Track
      {
         var _loc4_:ISortedList = this.buildSortedInteractionsList(param1);
         return this.computeBoufballTrajectory(_loc4_,param2,param3);
      }

      private function buildSortedInteractionsList(param1:ResolutionScenarioMessage) : ISortedList
      {
         var _loc3_:InteractionEntry = null;
         var _loc2_:ISortedList = new SortedArray(new InteractionDetailsComparator());
         for each(_loc3_ in param1.interaction)
         {
            _loc2_.addItem(_loc3_.interactionDetails);
         }
         return _loc2_;
      }

      private function computeBoufballTrajectory(param1:ISortedList, param2:HexPoint, param3:CommonData) : Track
      {
         var _loc6_:InteractionDetails = null;
         var _loc7_:HexPoint = null;
         var _loc4_:Track = new Track();
         _loc4_.addPosition(0,param2);
         var _loc5_:IIterator = param1.getIterator();
         while(_loc5_.hasNext())
         {
            _loc6_ = _loc5_.getNext();
            _loc7_ = this.getBallPosition(_loc6_,param3);
            if(_loc7_ != null)
            {
               _loc4_.addPosition(_loc6_.startTick,_loc7_);
            }
         }
         return _loc4_;
      }

      private function getBallPosition(param1:InteractionDetails, param2:CommonData) : HexPoint
      {
         var _loc3_:ParticipantDetails = null;
         var _loc4_:BoufbowlerInfos = null;
         var _loc5_:ParticipantDetails = null;
         var _loc6_:ParticipantDetails = null;
         for each(_loc3_ in param1.participants)
         {
            if(_loc3_.hasBall)
            {
               _loc4_ = param2.getBoufbowlerInfos(_loc3_.boufbowlerId);
               return _loc4_.getPositionAt(param1.startTick);
            }
         }
         // Missed attempts are visual cues along an uninterrupted ball flight.
         if((param1.type == InteractionType.RECEPTION || param1.type == InteractionType.INTERCEPTION)
            && param1.hasManeuverTest && !param1.maneuverTest.success) return null;
         switch(param1.type)
         {
            case InteractionType.REBOUND:
               return new HexPoint(param1.onGroundDetails.groundPosition.x,param1.onGroundDetails.groundPosition.y);
            case InteractionType.RECEPTION:
               _loc5_ = param1.participants[0];
               _loc4_ = param2.getBoufbowlerInfos(_loc5_.boufbowlerId);
               return _loc4_.getPositionAt(param1.startTick);
            case InteractionType.INTERCEPTION:
               _loc6_ = param1.participants[0];
               _loc4_ = param2.getBoufbowlerInfos(_loc6_.boufbowlerId);
               return _loc4_.getPositionAt(param1.startTick);
            default:
               return null;
         }
      }
   }
}
