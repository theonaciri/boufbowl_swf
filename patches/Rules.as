package com.ankamagames.boufbowl.client.match.strategic.model
{
   import as3.collections.IList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.match.model.OrderModel;
   import com.ankamagames.boufbowl.protocol.RegularOrderData.Element;

   public class Rules
   {

      public static const PASS_ELEMENT:int = Element.AIR;

      public static var passBaseRange:Number = 7;

      public static var passAirRangeModifier:Number = 1;

      public static var passRangeMultiplier:Number = 1;

      private var _constants:RulesConstants;

      public function Rules(param1:RulesConstants)
      {
         super();
         this._constants = param1;
      }

      public function getReferenceDistance(param1:IList) : Number
      {
         var _loc2_:Number = 0;
         var _loc3_:IIterator = param1.getIterator();
         while(_loc3_.hasNext())
         {
            _loc2_ += this.distanceByElement(_loc3_.getNext());
         }
         return _loc2_;
      }

      public function getMaxDistance(param1:Number) : Number
      {
         return param1 * this._constants.getMaxDistanceFactor();
      }

      public function canPassBall(param1:OrderModel) : Boolean
      {
         if(param1.emptyOrder)
         {
            return false;
         }
         return param1.elements.hasItem(PASS_ELEMENT);
      }

      public function getMaxPassDistance(elements:IList) : Number
      {
         var airOrders:int = 0;
         var iterator:IIterator = elements.getIterator();
         while(iterator.hasNext())
         {
            if(iterator.getNext() == PASS_ELEMENT) airOrders++;
         }
         return (passBaseRange + airOrders * passAirRangeModifier) * passRangeMultiplier;
      }

      private function distanceByElement(param1:int) : Number
      {
         var _loc2_:Number = NaN;
         switch(param1)
         {
            case Element.EARTH:
               _loc2_ = this._constants.getEarthDistanceBonus();
               break;
            case Element.FIRE:
               _loc2_ = this._constants.getFireDistanceBonus();
               break;
            case Element.AIR:
               _loc2_ = this._constants.getAirDistanceBonus();
               break;
            case Element.WATER:
               _loc2_ = this._constants.getWaterDistanceBonus();
               break;
            default:
               _loc2_ = 0;
         }
         return _loc2_;
      }
   }
}
