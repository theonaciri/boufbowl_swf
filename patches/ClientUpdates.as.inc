      // HTTPS notification only. Native package execution is handled by the
      // signed desktop bootstrap / Android installer, never downloaded AS3.
      private static const CLIENT_RELEASE:String = @RELEASE_VERSION@;
      private static const UPDATE_ORIGIN:String = @UPDATE_ORIGIN@;
      private static var updateButton:Sprite;
      private static var updateDownload:String;

      private static function compareRelease(first:String,second:String):int
      {
         if(!/^\d+\.\d+\.\d+$/.test(first) || !/^\d+\.\d+\.\d+$/.test(second)) return 0;
         var a:Array=first.split(".");var b:Array=second.split(".");
         for(var i:int=0;i<3;i++) if(int(a[i])!=int(b[i])) return int(a[i])>int(b[i]) ? 1 : -1;
         return 0;
      }

      private static function checkClientUpdate():void
      {
         if(!@ANDROID_UPDATE@) return;
         var loader:URLLoader=new URLLoader();
         var timer:uint=setTimeout(function():void { try { loader.close(); } catch(error:Error) {} },10000);
         loader.addEventListener(IOErrorEvent.IO_ERROR,function(event:IOErrorEvent):void { clearTimeout(timer); });
         loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR,function(event:SecurityErrorEvent):void { clearTimeout(timer); });
         loader.addEventListener(Event.COMPLETE,function(event:Event):void {
            clearTimeout(timer);
            try {
               if(String(loader.data).length>131072)return;
               var envelope:Object=com.adobe.serialization.json.JSON.decode(String(loader.data));
               var manifest:Object=com.adobe.serialization.json.JSON.decode(String(envelope.payload));
               if(manifest.schema!=1 || manifest.platforms==null || manifest.platforms.android==null)return;
               var item:Object=manifest.platforms.android;
               if(compareRelease(String(item.version),CLIENT_RELEASE)<=0 || String(item.url).indexOf(UPDATE_ORIGIN+"/downloads/")!=0)return;
               updateDownload=String(item.url);
               updateButton=serverAction(toolbar,"Mise à jour "+String(item.version),265,0,180,function():void {
                  // Never open the installer/download in the middle of a match.
                  if(serverCurrentMatch!=null || serverSpectating!=null) {
                     serverStatus("Mise à jour disponible. Terminez votre match avant de la télécharger.",true);return;
                  }
                  navigateToURL(new URLRequest(updateDownload),"_blank");
               });
               serverLayoutToolbar();
            } catch(error:Error) { /* Updates must never prevent the game from starting. */ }
         });
         try { loader.load(new URLRequest(UPDATE_ORIGIN+"/updates.json?check="+getTimer())); }
         catch(error:Error) { clearTimeout(timer); }
      }
