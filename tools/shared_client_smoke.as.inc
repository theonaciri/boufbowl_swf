      private function smokeAssert(condition:Boolean, message:String) : void
      {
         if(!condition) throw new Error(message);
      }

      private function smokeExit(code:int) : void
      {
         Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit(code);
      }

      private function runSharedSmoke(nativeExit:Boolean = false) : Object
      {
         try
         {
            if(nativeExit) smokeAssert(!ruffleRuntime,"Expected the native AIR runtime path");
            smokeAssert(stage.frameRate <= 30,"Saved FPS limit was exceeded");
            smokeAssert(readFrameRatePreference({}) == 0,"Unset FPS preference became an explicit cap");
            smokeAssert(readFrameRatePreference({frameRateTarget:30}) == 30,"Saved FPS preference was lost");
            smokeAssert(readFrameRatePreference({frameRateTarget:240}) == 240,"Valid high FPS preference was lost");
            smokeAssert(readFrameRatePreference({frameRateTarget:NaN,limitFrameRate25:true}) == 25,"Legacy FPS cap was lost");
            smokeAssert(readFrameRatePreference({frameRateTarget:300}) == 0,"Invalid FPS preference was accepted");
            for each(var invalidRate:Number in [24,241,NaN,Infinity,-Infinity])
               smokeAssert(readFrameRatePreference({frameRateTarget:invalidRate}) == 0,"Out-of-range FPS preference was accepted");
            var wasRuffle:Boolean = ruffleRuntime;
            var savedPreferred:Number = preferredFrameRate;
            var savedBrowser:Number = browserFrameRate;
            ruffleRuntime = false;
            preferredFrameRate = 0;
            smokeAssert(sceneFrameRate(50) == 50 && sceneFrameRate(25) == 25,"Native default scene rates changed");
            for each(var targetRate:Number in [25,30,50,60,90,120,144,240])
            {
               preferredFrameRate = targetRate;
               ruffleRuntime = false;
               smokeAssert(sceneFrameRate(50) == targetRate && sceneFrameRate(25) == targetRate,
                  "Native scene entry lost the selected FPS");
               browserFrameRate = targetRate;
               ruffleRuntime = true;
               smokeAssert(sceneFrameRate(50) == targetRate && sceneFrameRate(25) == targetRate,
                  "Browser scene entry lost the selected FPS");
            }
            ruffleRuntime = wasRuffle;
            preferredFrameRate = savedPreferred;
            browserFrameRate = savedBrowser;
            var sessionCheck:Object = sessionSmoke();
            var presenter:com.ankamagames.boufbowl.resolution.display.presenter.MovieClipSpritePresenter =
               new com.ankamagames.boufbowl.resolution.display.presenter.MovieClipSpritePresenter(1);
            presenter.sprite = new Sprite();
            var point:com.ankamagames.xgaming.utils.math.geom.Point3 =
               new com.ankamagames.xgaming.utils.math.geom.Point3(3,4,5);
            presenter.position = point;
            // Reading the vertex consumes its pending position change, as the
            // renderer does. Then clear the renderer's dirty flag.
            smokeAssert(presenter.sprite3d.x == 3,"Initial position was lost");
            presenter.sprite3d.vertexDirty = false;
            for(var i:int=0;i<1000;i++) presenter.position = point;
            smokeAssert(!presenter.sprite3d.vertexDirty,"Identical positions still invalidate the 3D object");
            presenter.position = new com.ankamagames.xgaming.utils.math.geom.Point3(4,4,5);
            smokeAssert(presenter.sprite3d.x == 4 && presenter.sprite3d.y == 5 && presenter.sprite3d.z == 4 && presenter.sprite3d.vertexDirty,
               "Movement or coordinate mapping was lost");
            presenter.sprite3d.vertexDirty = false;
            presenter.invalidate();
            smokeAssert(presenter.sprite3d.x == 4 && presenter.sprite3d.vertexDirty,"Explicit animation invalidation was lost");
            presenter.sprite3d.vertexDirty = false;
            presenter.sprite = new Sprite();
            smokeAssert(presenter.sprite3d.x == 4 && presenter.sprite3d.vertexDirty,"Replacing a stationary sprite did not invalidate it");
            var rejected:Boolean = false;
            try { presenter.position = new com.ankamagames.xgaming.utils.math.geom.Point3(NaN,1,2); }
            catch(invalid:Error) { rejected = true; }
            smokeAssert(rejected && presenter.sprite3d.x == 4,"Invalid coordinates changed the sprite");
            presenter.destroy();

            var frame:com.ankamagames.boufbowl.utils.FrameController = new com.ankamagames.boufbowl.utils.FrameController(0);
            frame.totalFrames = 3;
            var completions:int = 0;
            frame.addEventListener(com.ankamagames.boufbowl.utils.FrameController.LAST_FRAME_REACHED,
               function(event:Event):void { completions++; });
            frame.update(0,0);
            smokeAssert(frame.currentFrame == 0 && !frame.lastFrameReached,"Animation did not start at frame zero");
            for(i=0;i<1000;i++) frame.update(1000+i,1000+i);
            smokeAssert(frame.lastFrameReached && completions == 1,"Finished animation repeatedly dispatched completion");
            frame = new com.ankamagames.boufbowl.utils.FrameController(0,-1,false,false);
            frame.totalFrames = 20;
            frame.update(100,100);
            frame.update(100,100);
            smokeAssert(frame.currentFrame == 1,"An animation that forbids skipping stopped advancing");
            frame = new com.ankamagames.boufbowl.utils.FrameController(100);
            frame.totalFrames = 20;
            frame.update(99,99);
            smokeAssert(frame.currentFrame == -1,"Animation started before its scheduled time");
            frame = new com.ankamagames.boufbowl.utils.FrameController(0,1000);
            frame.totalFrames = 20;
            frame.setLoop(3,7);
            frame.update(500,500);
            smokeAssert(!frame.lastFrameReached && frame.currentFrame >= 3 && frame.currentFrame <= 7,"Animation loop timing changed");

            var scene:com.ankamagames.boufbowl.resolution.display.model.SceneModel = new com.ankamagames.boufbowl.resolution.display.model.SceneModel(
               new com.ankamagames.boufbowl.resolution.display.model.MobileFactory(),null);
            var ids:Array = [new com.netease.protobuf.Int64(23,1),new com.netease.protobuf.Int64(3,12),
               new com.netease.protobuf.Int64(0xffffffff,-1),new com.netease.protobuf.Int64(0x7fffffff,-1)];
            var actors:Array = [];
            for(i=0;i<ids.length;i++) actors.push(scene.addBoufbowler(ids[i],null,null));
            for(i=0;i<500;i++)
            {
               var id:com.netease.protobuf.Int64 = ids[i % ids.length];
               smokeAssert(scene.getBoufbowler(new com.netease.protobuf.Int64(id.low,id.high)) === actors[i % ids.length],
                  "Equivalent 64-bit ids resolved to different characters");
            }
            smokeAssert(scene.removeBoufbowler(new com.netease.protobuf.Int64(23,1)) === actors[0],"Removing by equivalent id failed");
            rejected = false;
            try { scene.getBoufbowler(new com.netease.protobuf.Int64(23,1)); }
            catch(missing:Error) { rejected = true; }
            smokeAssert(rejected,"Removed character remained in the lookup cache");
            var replacement:Object = scene.addBoufbowler(new com.netease.protobuf.Int64(23,1),null,null);
            smokeAssert(scene.getBoufbowler(new com.netease.protobuf.Int64(23,1)) === replacement,"Re-added character reused a stale cache entry");
            for(i=0;i<ids.length;i++) scene.removeBoufbowler(ids[i]);
            smokeAssert(scene.boufbowlers().numItems == 0,"Character removals left stale roster entries");

            var zone:com.ankamagames.xgaming.ui.components.TextZone = new com.ankamagames.xgaming.ui.components.TextZone();
            zone.defaultFontFamily = "VerdanaCFF";
            zone.defaultFontSize = 12;
            zone.setSize(240,60);
            zone.setContent("");
            zone.updateNow();
            smokeAssert(zone.viewportRatio == 1 && zone.preferedScrollStepRatio == 0 && !zone.canScroll(),
               "Empty chat has invalid scroll metrics");
            var changes:int = 0;
            zone.addEventListener(Event.CHANGE,function(event:Event):void { changes++; });
            for(i=0;i<25;i++)
            {
               var paragraph:flashx.textLayout.elements.ParagraphElement = new flashx.textLayout.elements.ParagraphElement();
               var span:flashx.textLayout.elements.SpanElement = new flashx.textLayout.elements.SpanElement();
               span.text = "Message " + i + " — Équipe précision réception";
               paragraph.addChild(span);
               zone.appendParagraph(paragraph);
            }
            zone.scrollRatio = 1;
            zone.updateNow();
            smokeAssert(changes == 1,"Chat recomposed before its explicit batch update");
            smokeAssert(zone.canScroll() && zone.viewportRatio > 0 && zone.viewportRatio < 1 && zone.scrollRatio == 1,
               "Long chat content cannot scroll to the bottom");
            for(i=0;i<500;i++) zone.updateNow();
            smokeAssert(changes == 1,"Unchanged chat content was recomposed");
            var previousViewport:Number = zone.viewportRatio;
            zone.setSize(240,120);
            zone.updateNow();
            smokeAssert(changes == 2 && zone.viewportRatio > previousViewport,"Resizing chat did not recompose its layout");
            zone.setSize(240,120);
            zone.updateNow();
            smokeAssert(changes == 2,"Unchanged chat dimensions triggered composition");
            zone.setPaddings(10,10,10,10);
            zone.updateNow();
            smokeAssert(changes == 3,"Changed chat padding did not recompose its layout");
            zone.scrollRatio = NaN;
            smokeAssert(zone.scrollRatio == 0,"NaN reached chat scroll state");
            zone.scrollRatio = Number.POSITIVE_INFINITY;
            smokeAssert(zone.scrollRatio == 1,"Infinite chat scroll was not bounded");
            zone.setContent("");
            zone.updateNow();
            smokeAssert(zone.viewportRatio == 1 && zone.controller.verticalScrollPosition == 0,
               "Clearing chat left an invalid text offset");
            var benchmark:Object = performanceBenchmark();
            trace("SHARED_SMOKE BENCHMARK moves=" + benchmark.moves + " previousMs=" + benchmark.previousMs + " batchedMs=" + benchmark.batchedMs);
            benchmark = lookupBenchmark();
            trace("SHARED_SMOKE LOOKUP lookups=" + benchmark.lookups + " previousMs=" + benchmark.previousMs + " indexedMs=" + benchmark.indexedMs);
            trace("SHARED_SMOKE PASS: movement, invalidation, chat batching and scroll boundaries");
            return {ok:true,runtime:ruffleRuntime ? "ruffle" : "native-path",fps:stage.frameRate,lookup:benchmark,session:sessionCheck};
         }
         catch(error:Error)
         {
            trace("SHARED_SMOKE FAIL: " + error.toString());
            if(nativeExit) smokeExit(1);
            return {ok:false,error:error.toString()};
         }
      }

      private function sessionSmoke() : Object
      {
         var session:away3d.core.session.SpriteSession = new away3d.core.session.SpriteSession();
         var view:away3d.containers.View3D = new away3d.containers.View3D({session:session,forceUpdate:true,mouseEvents:false});
         view.visible = false;
         addChild(view);
         view.render();
         var additions:int = 0;
         var removals:int = 0;
         var actors:Array = [];
         for(var index:int=0;index<4;index++)
         {
            var actor:Sprite = new Sprite();
            actor.addEventListener(Event.ADDED_TO_STAGE,function(event:Event):void { additions++; });
            actor.addEventListener(Event.REMOVED_FROM_STAGE,function(event:Event):void { removals++; });
            actors.push(actor);
         }
         var container:Sprite = Sprite(session.getContainer(view));
         try
         {
            sessionDraw(session,view,[actors[0],actors[1],actors[2]]);
            for(index=0;index<20;index++) sessionDraw(session,view,[actors[0],actors[1],actors[2]]);
            smokeAssert(additions == 3 && removals == 0,"Stable scene children were detached during redraw");
            sessionDraw(session,view,[actors[2],actors[1],actors[0]]);
            smokeAssert(container.getChildAt(0) == actors[2] && container.getChildAt(2) == actors[0],"Painter order was lost");
            smokeAssert(additions == 3 && removals == 0,"Reordering triggered stage lifecycle events");
            sessionDraw(session,view,[actors[2],actors[0]]);
            smokeAssert(container.numChildren == 2 && removals == 1,"Culled child was retained");
            sessionDraw(session,view,[actors[2],actors[0],actors[2],actors[3]]);
            smokeAssert(container.numChildren == 3 && container.getChildAt(0) == actors[0] &&
               container.getChildAt(1) == actors[2] && container.getChildAt(2) == actors[3],"Duplicate draw ordering changed");
            smokeAssert(additions == 4 && removals == 1,"A newly visible child did not enter stage exactly once");
            sessionDraw(session,view,[actors[0],null,actors[2],null,actors[3]]);
            smokeAssert(container.numChildren == 5 && container.getChildAt(0) == actors[0] &&
               container.getChildAt(2) == actors[2] && container.getChildAt(4) == actors[3],"Shape layers changed actor order");
            sessionDraw(session,view,[actors[3],null,actors[0],null,actors[2]]);
            smokeAssert(container.numChildren == 5 && container.getChildAt(0) == actors[3] &&
               container.getChildAt(2) == actors[0] && container.getChildAt(4) == actors[2],"Pooled shape layers changed painter order");
            sessionDraw(session,view,[]);
            smokeAssert(container.numChildren == 0 && removals == 4,"Empty scene left stale children");
            sessionDraw(session,view,[actors[1]]);
            smokeAssert(container.numChildren == 1 && additions == 5,"Hidden actor could not return");
            view.forceUpdate = false;
            session.clear(view);
            smokeAssert(!session.updated,"Unchanged session unexpectedly required redraw");
            session.render(view);
            smokeAssert(container.numChildren == 1 && container.getChildAt(0) == actors[1] && additions == 5,
               "Unchanged session lost its retained child");
            return {ok:true,additions:additions,removals:removals};
         }
         finally { removeChild(view); }
      }

      private function sessionDraw(session:away3d.core.session.SpriteSession, view:away3d.containers.View3D, sequence:Array) : void
      {
         session.clear(view);
         for each(var child:Sprite in sequence)
         {
            if(child == null) session.renderLine(0,0,10,10,1,0xff0000,1);
            else session.addDisplayObject(child);
         }
         session.render(view);
      }
