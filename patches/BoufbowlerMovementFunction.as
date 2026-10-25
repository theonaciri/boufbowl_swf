package com.ankamagames.boufbowl.client.match.resolution.interactions
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.resolution.display.script.CommonInteractionFunctions;
   import com.ankamagames.boufbowl.resolution.display.script.InteractionRoles;
   import com.ankamagames.boufbowl.resolution.display.script.ParticipantData;
   import com.ankamagames.boufbowl.resolution.display.script.runner.IBoufbowlerReference;
   import com.ankamagames.boufbowl.resolution.display.model.movement.Physics;
   import com.ankamagames.xgaming.utils.math.geom.Point3;
   import com.ankamagames.xgaming.utils.math.geom.hexaToOrtho;
   import com.ankamagames.boufbowl.protocol.TrackItem;
   import com.ankamagames.boufbowl.protocol.TrackItemType;
   import com.ankamagames.boufbowl.protocol.MovementSequence;
   
   public class BoufbowlerMovementFunction extends CommonInteractionFunctions
   {
      
      private var _duration:int;
      
      public function BoufbowlerMovementFunction(param1:ParticipantData, param2:int)
      {
         var _loc3_:IMap = new Map();
         _loc3_.addItem(InteractionRoles.ONLY_PARTICIPANT,param1);
         this._duration = param2;
         super(_loc3_);
      }
      
      public static function presentationItems(items:Array) : Array
      {
         var result:Array = [];
         for each(var item:TrackItem in items)
         {
            if(item.type != TrackItemType.MOVEMENT || item.movement.positions.length <= 1)
            {
               result.push(item);
               continue;
            }
            var previous:TrackItem = result.length > 0 ? result[result.length - 1] : null;
            var canMerge:Boolean = previous != null && previous.type == TrackItemType.MOVEMENT &&
               previous.movement.positions.length > 1 && previous.movement.endTick == item.movement.startTick;
            if(canMerge)
            {
               var end:Object = previous.movement.positions[previous.movement.positions.length - 1];
               var start:Object = item.movement.positions[0];
               canMerge = end.x == start.x && end.y == start.y;
            }
            if(canMerge)
            {
               for(var cell:int = 1; cell < item.movement.positions.length; cell++)
                  previous.movement.positions.push(item.movement.positions[cell]);
               previous.movement.endTick = item.movement.endTick;
            }
            else
            {
               // Clone only moving entries. Do not mutate the wire message or
               // merge across stationary waits, gaps or interaction boundaries.
               var copy:TrackItem = new TrackItem();
               copy.type = TrackItemType.MOVEMENT;
               copy.movement = new MovementSequence();
               copy.movement.startTick = item.movement.startTick;
               copy.movement.endTick = item.movement.endTick;
               for each(var point:Object in item.movement.positions) copy.movement.positions.push(point);
               result.push(copy);
            }
         }
         return result;
      }

      public static function travelDuration(data:ParticipantData, scheduledDuration:int) : int
      {
         if(scheduledDuration <= 0 || data.trajectoryLength <= 1) return 0;
         var previous:Point3 = Point3.fromPoint2(hexaToOrtho(data.startPosition));
         var distance:Number = 0;
         for(var cell:int = 2; cell <= data.trajectoryLength; cell++)
         {
            var next:Point3 = Point3.fromPoint2(hexaToOrtho(data.getNthCell(cell)));
            distance += next.subtract(previous).length;
            previous = next;
         }
         if(distance == 0) return 0;
         // Spend as much of the scheduled slot running as possible, with
         // at most 30% slowdown relative to the retained normal velocity.
         var maximumTravelDuration:int = Math.max(1,Math.floor(distance * Physics.VELOCITY_TIME_UNIT / (Physics.DEFAULT_VELOCITY * 0.7)));
         return Math.min(scheduledDuration,maximumTravelDuration);
      }

      override public function buildNodes() : void
      {
         var boufbowler:IBoufbowlerReference = getBoufbowler(InteractionRoles.ONLY_PARTICIPANT);
         var data:ParticipantData = getData(InteractionRoles.ONLY_PARTICIPANT);
         if(data.trajectoryLength <= 1 || this._duration <= 0)
         {
            simpleMovement(data,boufbowler,this._duration);
            return;
         }
         var travel:int = travelDuration(data,this._duration);
         simpleMovement(data,boufbowler,travel);
         if(travel < this._duration)
         {
            then();
            // Arrival stops the run animation; the queue waits here so later
            // combat/pass/pickup nodes keep their existing scheduled time.
            wait(this._duration - travel);
         }
      }

   }
}

