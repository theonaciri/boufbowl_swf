      private function smokeAssert(condition:Boolean, message:String) : void
      {
         if(!condition) throw new Error(message);
      }

      private function smokeExit(code:int) : void
      {
         Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit(code);
      }

      private function runSharedSmoke() : void
      {
         try
         {
            smokeAssert(!ruffleRuntime,"Expected the native AIR runtime path");
            smokeAssert(stage.frameRate <= 30,"Saved FPS limit was exceeded");
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
            presenter.destroy();

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
            zone.scrollRatio = NaN;
            smokeAssert(zone.scrollRatio == 0,"NaN reached chat scroll state");
            zone.scrollRatio = Number.POSITIVE_INFINITY;
            smokeAssert(zone.scrollRatio == 1,"Infinite chat scroll was not bounded");
            zone.setContent("");
            zone.updateNow();
            smokeAssert(zone.viewportRatio == 1 && zone.controller.verticalScrollPosition == 0,
               "Clearing chat left an invalid text offset");
            trace("SHARED_SMOKE PASS: movement, invalidation, chat batching and scroll boundaries");
         }
         catch(error:Error)
         {
            trace("SHARED_SMOKE FAIL: " + error.toString());
            smokeExit(1);
         }
      }
