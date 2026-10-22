private function performanceBenchmark():Object {
         var count:int=3000;
         var presenter:com.ankamagames.boufbowl.resolution.display.presenter.MovieClipSpritePresenter = new com.ankamagames.boufbowl.resolution.display.presenter.MovieClipSpritePresenter(1);
         presenter.sprite=new Sprite();
         var sprite:away3d.sprites.Sprite3D=presenter.sprite3d;
         var point:com.ankamagames.xgaming.utils.math.geom.Point3=new com.ankamagames.xgaming.utils.math.geom.Point3(0,0,0);
         var points:Array=[];for(var n:int=0;n<count;n++) points.push(new com.ankamagames.xgaming.utils.math.geom.Point3(n%25,n%13,n%5));
         var start:int=getTimer();
         for(var i:int=0;i<count;i++) {
            sprite.x=Number.MAX_VALUE;sprite.y=Number.MAX_VALUE;sprite.z=Number.MAX_VALUE;
            point=points[i];sprite.x=point.x;sprite.y=point.z;sprite.z=point.y;
         }
         var oldTime:int=getTimer()-start;
         start=getTimer();
         for(i=0;i<count;i++) {
            presenter.position=points[i];
         }
         var newTime:int=getTimer()-start;
         presenter.destroy();
         return {moves:count,previousMs:oldTime,batchedMs:newTime};
      }
