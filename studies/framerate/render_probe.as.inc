      public static var renderProfile:Object = {};
      public static function studyProfile(kind:String, start:int):void {
         var elapsed:int=flash.utils.getTimer()-start;
         if(renderProfile[kind]==null)renderProfile[kind]={count:0,ms:0,max:0};
         var bucket:Object=renderProfile[kind];bucket.count++;bucket.ms+=elapsed;bucket.max=Math.max(bucket.max,elapsed);
      }
      private function initializeRenderingStudy():void {
         flash.external.ExternalInterface.addCallback("studyRenderProfile",function(reset:Boolean=false):Object {
            if(reset)renderProfile={};return renderProfile;
         });
         flash.external.ExternalInterface.addCallback("studySessionCheck",sessionSmoke);
         flash.external.ExternalInterface.addCallback("studySessionBench",function(iterations:int=300,leaves:int=30):Object {
            var session:away3d.core.session.SpriteSession=new away3d.core.session.SpriteSession();
            var view:away3d.containers.View3D=new away3d.containers.View3D({session:session,forceUpdate:true,mouseEvents:false});
            view.visible=false;addChild(view);
            var actors:Array=[];var added:int=0;var removed:int=0;
            for(var actorIndex:int=0;actorIndex<10;actorIndex++) {
               var actor:Sprite=new Sprite();
               for(var childIndex:int=0;childIndex<leaves;childIndex++) {
                  var leaf:Sprite=new Sprite();
                  leaf.graphics.beginFill(0x3578cf);leaf.graphics.drawCircle(0,0,3);leaf.graphics.endFill();
                  leaf.addEventListener(Event.ADDED_TO_STAGE,function(event:Event):void {added++;});
                  leaf.addEventListener(Event.REMOVED_FROM_STAGE,function(event:Event):void {removed++;});
                  actor.addChild(leaf);
               }
               actors.push(actor);
            }
            var start:int=flash.utils.getTimer();
            try {
               for(var frameIndex:int=0;frameIndex<iterations;frameIndex++) {
                  session.clear(view);
                  for(actorIndex=0;actorIndex<10;actorIndex++) {
                     actor=actors[actorIndex];actor.x=frameIndex%100;
                     session.addDisplayObject(actor);
                  }
                  session.render(view);
               }
               return {iterations:iterations,actors:10,leavesPerActor:leaves,elapsedMs:flash.utils.getTimer()-start,
                  stageAdditions:added,stageRemovals:removed};
            } finally {removeChild(view);}
         });
      }
