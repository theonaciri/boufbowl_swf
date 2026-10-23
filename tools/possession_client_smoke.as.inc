      private function findPossessionView(container:flash.display.DisplayObjectContainer):Object
      {
         for(var index:int=0;index<container.numChildren;index++)
         {
            var child:flash.display.DisplayObject=container.getChildAt(index);
            if(child is com.ankamagames.boufbowl.client.match.strategic.view.field.boufbowler.BoufbowlerFieldRepresentationView)
               return child;
            if(child is flash.display.DisplayObjectContainer)
            {
               var found:Object=findPossessionView(flash.display.DisplayObjectContainer(child));
               if(found != null) return found;
            }
         }
         return null;
      }

      private var possessionLiveStarted:int=0;
      private var possessionLiveView:Object;

      private function possessionLive(rate:int=0):Object
      {
         if(possessionLiveView==null) possessionLiveView=findPossessionView(this);
         var view:Object=possessionLiveView;
         if(view==null) return {ready:false};
         if(rate>0)
         {
            // Apply stage changes outside Ruffle's ExternalInterface callback.
            setTimeout(function():void {
               stage.frameRate=rate;
               view.hasBall=false;view.hasBall=true;
               possessionLiveStarted=getTimer();
            },1);
            return {ready:true,pending:true};
         }
         return {ready:true,elapsed:getTimer()-possessionLiveStarted,stageRate:stage.frameRate,state:view.possessionProbeInfo()};
      }

      private function possessionSmoke():Object
      {
         var view:Object=findPossessionView(this);
         if(view==null) return {ready:false};
         var original:Object=view.possessionProbeInfo();
         var parent:flash.display.DisplayObjectContainer=view.parent;
         var originalIndex:int=parent.getChildIndex(view);
         var viewClass:Class=getDefinitionByName("com.ankamagames.boufbowl.client.match.strategic.view.field.boufbowler.BoufbowlerFieldRepresentationView") as Class;
         var rates:Array=[];
         var result:Object;
         try
         {
            smokeAssert(original.totalFrames>1,"Possession asset has no animated timeline");
            for each(var rate:int in [25,30,50,60,90,120,144,240])
            {
               viewClass.possessionProbeTime=0;
               view.hasBall=false;view.hasBall=true;
               var period:int=original.totalFrames*40;
               var duration:int=period*2;
               var updates:int=Math.ceil(duration*rate/1000);
               for(var index:int=0;index<=updates;index++)
               {
                  var time:int=Math.min(duration,Math.round(index*1000/rate));
                  viewClass.possessionProbeTime=time;view.possessionProbeTick();
                  smokeAssert(view.currentFrame==1+int(time/40)%original.totalFrames,"Display rate changed possession animation timing");
               }
               smokeAssert(view.currentFrame==1,"Possession animation did not loop to its first frame");
               rates.push({target:rate,periodMs:period,updates:updates+1,finalFrame:view.currentFrame});
            }
            viewClass.possessionProbeTime=0;view.hasBall=false;view.hasBall=true;
            viewClass.possessionProbeTime=39;view.possessionProbeTick();
            smokeAssert(view.currentFrame==1,"Possession advanced before the authored frame boundary");
            viewClass.possessionProbeTime=40;view.possessionProbeTick();
            smokeAssert(view.currentFrame==2,"Possession missed the authored frame boundary");
            viewClass.possessionProbeTime=0;view.hasBall=false;view.hasBall=true;
            viewClass.possessionProbeTime=200;view.possessionProbeTick();
            var repeatedFrame:int=view.currentFrame;
            view.hasBall=true;
            smokeAssert(view.currentFrame==repeatedFrame,"Repeated possession update restarted the marker");
            viewClass.possessionProbeTime=400;view.possessionProbeTick();
            smokeAssert(view.currentFrame==1+10%original.totalFrames,"Repeated update changed the clock origin");
            view.hasBall=false;
            var stopped:Object=view.possessionProbeInfo();
            smokeAssert(stopped.frame==1 && !stopped.running && !stopped.front && !stopped.back,"Possession loss left an active marker");
            viewClass.possessionProbeTime=0;view.hasBall=true;
            viewClass.possessionProbeTime=100;view.possessionProbeTick();
            var pausedFrame:int=view.currentFrame;
            parent.removeChild(view);
            viewClass.possessionProbeTime=10000;view.possessionProbeTick();
            smokeAssert(view.currentFrame==pausedFrame && !view.possessionProbeInfo().running,"Offstage marker kept advancing");
            parent.addChildAt(view,Math.min(originalIndex,parent.numChildren));
            viewClass.possessionProbeTime=10020;view.possessionProbeTick();
            smokeAssert(view.currentFrame==1+3%original.totalFrames,"Reattached marker lost its saved phase");
            view.hasBall=false;parent.removeChild(view);
            viewClass.possessionProbeTime=0;view.hasBall=true;
            viewClass.possessionProbeTime=1000;view.possessionProbeTick();
            smokeAssert(view.currentFrame==1 && !view.possessionProbeInfo().running,"Detached possession assignment started its clock");
            parent.addChildAt(view,Math.min(originalIndex,parent.numChildren));
            viewClass.possessionProbeTime=1040;view.possessionProbeTick();
            smokeAssert(view.currentFrame==2,"Detached possession assignment did not start on reattachment");
            result={ready:true,ok:true,asset:original,rates:rates,frameBoundary:true,repeatedAssignment:true,loss:true,detachResume:true,offstageAssignment:true};
         }
         catch(error:Error) {result={ready:true,ok:false,error:error.toString(),state:view.possessionProbeInfo()};}
         {
            if(view.parent==null)parent.addChildAt(view,Math.min(originalIndex,parent.numChildren));
            view.hasBall=false;viewClass.possessionProbeTime=-1;view.hasBall=original.hasBall;
         }
         return result;
      }
