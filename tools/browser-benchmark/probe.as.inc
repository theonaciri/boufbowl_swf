      private var benchmarkFrameTimes:Array = [];
      private var benchmarkFrameLast:int = 0;
      private var benchmarkRecording:Boolean = false;
      private var benchmarkCutsceneDone:Boolean = false;
      private var benchmarkMotion:Boolean = false;
      private var benchmarkMoved:Object = {};
      private var benchmarkMotionCount:int = 0;
      private var benchmarkInitialPositions:Object;

      private function benchmarkFrame(event:Event) : void
      {
         var now:int = getTimer();
         if(benchmarkFrameLast > 0) benchmarkFrameTimes.push(now-benchmarkFrameLast);
         benchmarkFrameLast = now;
         if(benchmarkMotion && benchmarkMotionCount < 10)
         {
            var positions:Object = benchmarkPositions();
            for(var id:String in positions)
            {
               var initial:Object = benchmarkInitialPositions[id];
               var current:Object = positions[id];
               if(!benchmarkMoved[id] && (initial.x != current.x || initial.y != current.y || initial.z != current.z))
               {
                  benchmarkMoved[id] = true;benchmarkMotionCount++;
               }
            }
         }
      }

      private function benchmarkSample(action:String) : Object
      {
         if(action == "start" || action == "motion")
         {
            benchmarkFrameTimes = [];benchmarkFrameLast = 0;benchmarkRecording = true;
            benchmarkMotion = action == "motion";benchmarkMoved = {};benchmarkMotionCount = 0;benchmarkInitialPositions = benchmarkPositions();
            addEventListener(Event.ENTER_FRAME,benchmarkFrame);
         }
         else
         {
            removeEventListener(Event.ENTER_FRAME,benchmarkFrame);benchmarkRecording = false;
         }
         return {movedActors:benchmarkMotionCount,positions:benchmarkPositions(),samples:benchmarkFrameTimes,target:stage.frameRate,render:AbstractSession.browserRenderStats()};
      }

      private function benchmarkPositions() : Object
      {
         var positions:Object = {};
         var scene:SceneController = SceneController.active;
         if(scene == null) return positions;
         var iterator:IIterator = scene.model.boufbowlers().getIterator();
         while(iterator.hasNext())
         {
            var id:Int64 = iterator.getNext();
            var point:Point3 = scene.model.getBoufbowler(id).position;
            positions[id.toString()] = {x:point.x,y:point.y,z:point.z};
         }
         return positions;
      }

      private function benchmarkState() : Object
      {
         var views:Array = [];
         var pending:Array = [stage];
         while(pending.length > 0)
         {
            var object:DisplayObject = pending.pop();
            var name:String = getQualifiedClassName(object);
            if((name.indexOf("MatchCreationView") >= 0 || name.indexOf("MatchmakingView") >= 0 || name.indexOf("WelcomeView") >= 0) || name.indexOf("FieldView") >= 0 || name.indexOf("ResolutionView") >= 0)
               views.push(name);
            var container:DisplayObjectContainer = object as DisplayObjectContainer;
            if(container != null) for(var i:int=0;i<container.numChildren;i++) pending.push(container.getChildAt(i));
         }
         var scene:SceneController = SceneController.active;
         var actors:int = 0;
         if(scene != null)
         {
            var actorIterator:IIterator = scene.model.boufbowlers().getIterator();
            while(actorIterator.hasNext()) { actorIterator.getNext();actors++; }
         }
         return {views:views,actors:actors,
            phase:measurementPhase,cutsceneDone:benchmarkCutsceneDone};
      }

      private function benchmarkCutscene(key:String) : void
      {
         var allowed:Array = ["Illustration_Terre_Terre","Illustration_lancer","Illustration_reception_ok_Air"];
         if(allowed.indexOf(key) < 0) throw new Error("Unknown benchmark cutscene");
         var scene:SceneController = SceneController.active;
         if(scene == null) throw new Error("3D scene is not ready");
         scene.pauseGame(0);
         var ids:ArrayList = new ArrayList();
         ids.addItem(new Int64(11,0));ids.addItem(new Int64(21,0));
         benchmarkCutsceneDone = false;
         scene.uiController.playCutScene(scene.updateRealTime,key,true,ids,new Int64(11,0),false,scene,
            function():void { benchmarkCutsceneDone = true; });
      }
