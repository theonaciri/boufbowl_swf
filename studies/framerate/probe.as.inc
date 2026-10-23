      public static var studyRate:Number = 0;
      public static var studySceneUpdates:int = 0;
      public static var studyUiUpdates:int = 0;
      public static var studyPositionWrites:int = 0;
      public static var studySceneRates:Object = {};
      public static var studyPolicyEnabled:Boolean = true;
      private var studyLast:int = 0;
      private var studyStart:int = 0;
      private var studyFrames:int = 0;
      private var studyDuplicates:int = 0;
      private var studyIntervals:Array = [];
      private var studyEnabled:Boolean = false;
      private var studyAnimation:com.ankamagames.boufbowl.utils.FrameController;
      private var studyPoseChanges:int = 0;

      private function initializeStudy():void {
         var root:BoufbowlClient=this;
         var launchRate:Number=browserFrameRate;
         flash.external.ExternalInterface.addCallback("studySettings",function():Object {
            return {launchBrowser:launchRate,browser:browserFrameRate,preferred:preferredFrameRate,
               scene50:sceneFrameRate(50),scene25:sceneFrameRate(25),stage:stage.frameRate,ruffle:ruffleRuntime};
         });
         flash.external.ExternalInterface.addCallback("studyWebDisplay",setWebDisplay);
         flash.external.ExternalInterface.addCallback("studySetRate",function(rate:Number):Object {
            studyRate=rate;
            var accepted:Boolean=true;
            if(loaderInfo.parameters.studyProductionPolicy == "1" && ruffleRuntime)
               accepted=setWebDisplay(rate,"low");
            else {browserFrameRate=rate;preferredFrameRate=rate;stage.frameRate=rate;}
            return {requested:rate,stage:stage.frameRate,accepted:accepted};
         });
         flash.external.ExternalInterface.addCallback("studyStart",function():Object {
            studyFrames=studyDuplicates=studyPoseChanges=0;studyIntervals=[];
            studySceneUpdates=studyUiUpdates=studyPositionWrites=0;
            studySceneRates={};
            studyStart=studyLast=flash.utils.getTimer();studyEnabled=true;
            studyAnimation=new com.ankamagames.boufbowl.utils.FrameController(0,100000);
            studyAnimation.totalFrames=25;studyAnimation.setLoop(1,25);
            studyAnimation.addEventListener(com.ankamagames.boufbowl.utils.FrameController.FRAME_CHANGED,
               function(event:Event):void {studyPoseChanges++;});
            return {start:studyStart,stage:stage.frameRate};
         });
         flash.external.ExternalInterface.addCallback("studyStop",function():Object {
            studyEnabled=false;
            return {elapsedMs:flash.utils.getTimer()-studyStart,frames:studyFrames,duplicates:studyDuplicates,
               intervals:studyIntervals,poseChanges:studyPoseChanges,sceneUpdates:studySceneUpdates,
               uiUpdates:studyUiUpdates,positionWrites:studyPositionWrites,sceneRates:studySceneRates,stage:stage.frameRate};
         });
         flash.external.ExternalInterface.addCallback("studySynthetic",studySynthetic);
         flash.external.ExternalInterface.addCallback("studyPolicy",function():Object {
            var saved:Number=preferredFrameRate;var savedBrowser:Number=browserFrameRate;
            var savedStage:Number=stage.frameRate;
            var savedRuffle:Boolean=ruffleRuntime;studyPolicyEnabled=false;
            preferredFrameRate=144;browserFrameRate=30;ruffleRuntime=false;
            var nativeRate:Number=sceneFrameRate(50);
            ruffleRuntime=true;var browserRate:Number=sceneFrameRate(50);
            var accepted:Boolean=setWebDisplay(144,"low");
            preferredFrameRate=saved;browserFrameRate=savedBrowser;ruffleRuntime=savedRuffle;studyPolicyEnabled=true;
            stage.frameRate=savedStage;
            return {nativeSceneAt144:nativeRate,browserSceneAt144:browserRate,web144Accepted:accepted,
               authoredHz:com.ankamagames.boufbowl.resolution.display.Constants.DEFAULT_FRAME_PER_MILLISECONDS*1000};
         });
         addEventListener(Event.ENTER_FRAME,function(event:Event):void {
            if(!studyEnabled) return;
            var now:int=flash.utils.getTimer();var delta:int=now-studyLast;
            studyLast=now;studyFrames++;studyIntervals.push(delta);if(delta==0)studyDuplicates++;
            studyAnimation.update(now-studyStart,now-studyStart);
         });
      }

      public static function studyRecordScene():void {
         studySceneUpdates++;
         var rate:String=String(measurementRoot.stage.frameRate);
         studySceneRates[rate]=int(studySceneRates[rate])+1;
      }

      private function studySynthetic():Object {
         var output:Array=[];
         for each(var rate:int in [25,30,50,60,90,120,144,240,1000,10000]) {
            var frames:Array=[];var completion:int=0;
            var trajectory:com.ankamagames.boufbowl.resolution.display.model.movement.SegmentTrajectory=new com.ankamagames.boufbowl.resolution.display.model.movement.SegmentTrajectory(
               new com.ankamagames.xgaming.utils.math.geom.Point3(0,0,0),new com.ankamagames.xgaming.utils.math.geom.Point3(100,50,10),0,1000);
            var previousX:Number=-1;var distinctPositions:int=0;var maximumStep:Number=0;var error:Number=0;
            var controller:com.ankamagames.boufbowl.utils.FrameController=new com.ankamagames.boufbowl.utils.FrameController(0);
            controller.totalFrames=25;
            controller.addEventListener(com.ankamagames.boufbowl.utils.FrameController.FRAME_CHANGED,
               function(event:Event):void {frames.push(controller.currentFrame);});
            controller.addEventListener(com.ankamagames.boufbowl.utils.FrameController.LAST_FRAME_REACHED,
               function(event:Event):void {completion++;});
            for(var index:int=0;index<=rate;index++) {
               var time:int=Math.round(index*1000/rate);
               controller.update(time,time);
               var point:com.ankamagames.xgaming.utils.math.geom.Point3=trajectory.getPosition(time);
               error=Math.max(error,Math.abs(point.x-time/10));
               if(point.x!=previousX){distinctPositions++;if(previousX>=0)maximumStep=Math.max(maximumStep,point.x-previousX);previousX=point.x;}
            }
            for(index=1001;index<1050;index++)controller.update(index,index);
            output.push({requested:rate,updates:rate+1,poseEvents:frames.length,lastPose:frames[frames.length-1],completion:completion,frames:frames,distinctPositions:distinctPositions,maximumStep:maximumStep,interpolationError:error,finalX:previousX});
         }
         return {rates:output};
      }
