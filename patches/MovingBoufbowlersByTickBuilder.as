package com.ankamagames.boufbowl.client.match.resolution.builder
{
   import as3.collections.ArrayList;
   import as3.collections.ILinkedMap;
   import as3.collections.IList;
   import as3.collections.LinkedMap;
   import com.ankamagames.boufbowl.protocol.BoufbowlerTrack;
   import com.ankamagames.boufbowl.protocol.ResolutionScenarioMessage;
   import com.ankamagames.boufbowl.protocol.TrackItem;
   import com.ankamagames.boufbowl.protocol.TrackItemType;
   import com.ankamagames.boufbowl.resolution.display.script.ParticipantData;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.BoufbowlerMovementFunction;
   
   internal final class MovingBoufbowlersByTickBuilder
   {
      
      public function MovingBoufbowlersByTickBuilder()
      {
         super();
      }
      
      public function build(message:ResolutionScenarioMessage, commonData:CommonData) : IList
      {
         var counts:ILinkedMap = new LinkedMap();
         var result:ArrayList = new ArrayList();
         var tick:uint;
         for(tick = 0; tick < message.turnEndTick; tick++) counts.addItem(tick,0);
         for each(var track:BoufbowlerTrack in message.boufbowlerTracks)
         {
            var infos:BoufbowlerInfos = commonData.getBoufbowlerInfos(track.boufbowlerId);
            var windows:Array = [];
            for each(var item:TrackItem in BoufbowlerMovementFunction.presentationItems(track.item))
            {
               if(item.type != TrackItemType.MOVEMENT) continue;
               var data:ParticipantData = commonData.relatedTurnParticipantData(item.movement.startTick,track.boufbowlerId);
               var duration:int = (item.movement.endTick - item.movement.startTick) * commonData.msPerTick;
               var travel:int = BoufbowlerMovementFunction.travelDuration(data,duration);
               windows.push({startTick:item.movement.startTick,endTick:item.movement.endTick,
                  arrivalTick:item.movement.startTick + travel / commonData.msPerTick});
            }
            for(tick = 0; tick < message.turnEndTick; tick++)
            {
               if(!infos.isMoving(tick)) continue;
               var moving:Boolean = true;
               for each(var window:Object in windows)
               {
                  if(tick >= window.startTick && tick < window.endTick && tick >= window.arrivalTick)
                  {
                     moving = false;
                     break;
                  }
               }
               if(moving) counts.addItem(tick,int(counts.getItem(tick)) + 1);
            }
         }
         var intervalStart:int = 0;
         var previousCount:int = -1;
         for(tick = 0; tick < message.turnEndTick; tick++)
         {
            var count:int = counts.getItem(tick);
            if(count != previousCount)
            {
               if(previousCount != -1) result.addItem(new BoufbowlerMovementData(intervalStart,tick,previousCount));
               intervalStart = tick;
               previousCount = count;
            }
         }
         result.addItem(new BoufbowlerMovementData(intervalStart,message.turnEndTick,previousCount));
         if(previousCount != 0) result.addItem(new BoufbowlerMovementData(message.turnEndTick,message.turnEndTick,0));
         return result;
      }

   }
}

