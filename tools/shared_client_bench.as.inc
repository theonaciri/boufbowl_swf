private function performanceBenchmark():Object {
         var count:int=3000;
         var presenter:com.ankamagames.boufbowl.resolution.display.presenter.MovieClipSpritePresenter = new com.ankamagames.boufbowl.resolution.display.presenter.MovieClipSpritePresenter(1);
         presenter.sprite=new Sprite();
         var sprite:away3d.sprites.Sprite3D=presenter.sprite3d;
         var point:com.ankamagames.xgaming.utils.math.geom.Point3=new com.ankamagames.xgaming.utils.math.geom.Point3(0,0,0);
         var points:Array=[];for(var n:int=0;n<count;n++) points.push(new com.ankamagames.xgaming.utils.math.geom.Point3(n%25,n%13,n%5));
         var start:int=flash.utils.getTimer();
         for(var i:int=0;i<count;i++) {
            sprite.x=Number.MAX_VALUE;sprite.y=Number.MAX_VALUE;sprite.z=Number.MAX_VALUE;
            point=points[i];sprite.x=point.x;sprite.y=point.z;sprite.z=point.y;
         }
         var oldTime:int=flash.utils.getTimer()-start;
         start=flash.utils.getTimer();
         for(i=0;i<count;i++) {
            presenter.position=points[i];
         }
         var newTime:int=flash.utils.getTimer()-start;
         presenter.destroy();
         return {moves:count,previousMs:oldTime,batchedMs:newTime};
      }

      private function lookupBenchmark():Object {
         var count:int=3000;
         var model:com.ankamagames.boufbowl.resolution.display.model.SceneModel = new com.ankamagames.boufbowl.resolution.display.model.SceneModel(
            new com.ankamagames.boufbowl.resolution.display.model.MobileFactory(),null);
         var previous:as3.collections.Map = new as3.collections.Map();
         for(var n:int=0;n<10;n++) {
            var id:com.netease.protobuf.Int64 = new com.netease.protobuf.Int64(n+1,0);
            previous.addItem(id,model.addBoufbowler(id,null,null));
         }
         var ids:Array=[];
         for(n=0;n<count;n++) ids.push(new com.netease.protobuf.Int64(n%10+1,0));
         var start:int=flash.utils.getTimer();
         var actor:Object;
         for(var i:int=0;i<count;i++) {
            id=ids[i];actor=previous.getItem(id);
            if(actor == null) {
               var iterator:as3.collections.iterators.IIterator=previous.getKeyIterator();
               while(iterator.hasNext()) {
                  var key:com.netease.protobuf.Int64=iterator.getNext();
                  if(key.equals(id)) { actor=previous.getItem(key);break; }
               }
            }
            if(actor == null) throw new Error("Baseline lookup lost a character");
         }
         var previousMs:int=flash.utils.getTimer()-start;
         start=flash.utils.getTimer();
         for(i=0;i<count;i++) actor=model.getBoufbowler(ids[i]);
         var indexedMs:int=flash.utils.getTimer()-start;
         return {lookups:count,previousMs:previousMs,indexedMs:indexedMs};
      }
