      // Disposable probe only: exact-pixel reuse, mutation invalidation and quality budget.
      private function runBrowserRenderSmoke() : Object
      {
         AbstractSession.configureBrowserRendering("original",true,false,true);
         var session:AbstractSession = new AbstractSession();
         var texture:BitmapData = new BitmapData(128,128,false,0x884422);
         var surface:Shape = new Shape();
         var xy:Vector.<Number> = Vector.<Number>([4,4,120,4,4,120]);
         var uvt:Vector.<Number> = Vector.<Number>([0,0,1,1,0,0.5,0,1,0.25]);
         var indices:Vector.<int> = Vector.<int>([0,1,2]);
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var first:Object = AbstractSession.browserRenderStats();
         var a:BitmapData = new BitmapData(128,128,true,0);
         a.draw(surface);
         surface.graphics.clear();
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var hit:Object = AbstractSession.browserRenderStats();
         var b:BitmapData = new BitmapData(128,128,true,0);
         b.draw(surface);
         var identical:Boolean = a.compare(b) === 0;
         texture.fillRect(texture.rect,0x228844);
         surface.graphics.clear();
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var changed:BitmapData = new BitmapData(128,128,true,0);changed.draw(surface);
         var livePixels:Boolean = b.compare(changed) !== 0;
         xy[0] += 1;
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var moved:Object = AbstractSession.browserRenderStats();
         uvt[2] = 0.9;
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var uvChanged:Object = AbstractSession.browserRenderStats();
         AbstractSession.configureBrowserRendering("low",false,false,true);
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var low:Object = AbstractSession.browserRenderStats();
         AbstractSession.configureBrowserRendering("original",false,false,true);
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var original:Object = AbstractSession.browserRenderStats();
         for(var k:int=0;k<140;k++) {
            AbstractSession.configureBrowserRendering("original",true,false,true);
            xy[0] = 4+k*0.01;
            session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         }
         AbstractSession.configureBrowserRendering("original",false,true,true);
         session.renderTriangleBitmap(texture,uvt,xy,indices,0,0,true,false,surface.graphics);
         var nativeStats:Object = AbstractSession.browserRenderStats();
         return {first:first,hit:hit,identical:identical,livePixels:livePixels,
            moved:moved,uvChanged:uvChanged,low:low,original:original,native:nativeStats};
      }
