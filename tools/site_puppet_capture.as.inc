         // Export-only callbacks: use the same Tiphon puppets as the team preview and match.
         var puppetModel:com.ankamagames.boufbowl.resolution.display.animation.BoufbowlerSprite;
         var puppetProvider:com.ankamagames.boufbowl.resolution.display.animation.IAnimationProvider;
         var puppetDisplay:flash.display.Sprite;
         var puppetBounds:flash.geom.Rectangle;
         var puppetClip:com.ankamagames.tiphon.types.ScriptedAnimation;
         var puppetStage:Stage=Stage(app.contextInjector.getInstance(Stage));
         var puppetConfig:IBoufbowlConfig=app.contextInjector.getInstance(IBoufbowlConfig);
         var puppetProxy:com.ankamagames.boufbowl.resolution.display.animation.TiphonProxy=new com.ankamagames.boufbowl.resolution.display.animation.TiphonProxy(puppetStage);
         puppetProxy.initPaths(puppetConfig.tiphonBonesPath,puppetConfig.tiphonSkinsPath,puppetConfig.tiphonIndexPath);
         var puppetFind:Function=function(container:flash.display.DisplayObjectContainer):com.ankamagames.tiphon.types.ScriptedAnimation {
            if(container is com.ankamagames.tiphon.types.ScriptedAnimation)return container as com.ankamagames.tiphon.types.ScriptedAnimation;
            for(var i:int=0;i<container.numChildren;i++){
               var child:flash.display.DisplayObject=container.getChildAt(i);
               if(child is flash.display.DisplayObjectContainer){var found:com.ankamagames.tiphon.types.ScriptedAnimation=puppetFind(child);if(found!=null)return found;}
            }
            return null;
         };
         flash.external.ExternalInterface.addCallback("puppetCreate",function(cls:int,gender:int,animation:String,hair:uint,skin:uint,eyes:uint):String {
            try {
               if(puppetProxy.state!=3)return "LOADING";
               if(puppetModel!=null)puppetModel.release();
               while(puppetStage.numChildren>0)puppetStage.removeChildAt(puppetStage.numChildren-1);
               puppetModel=new com.ankamagames.boufbowl.resolution.display.animation.BoufbowlerSprite(cls,gender,0,Color3.fromRgbUInt(hair),Color3.fromRgbUInt(eyes),Color3.fromRgbUInt(skin),Color3.fromRgbUInt(0xb51e27));
               puppetProvider=puppetModel.getAnimationProvider();
               puppetProvider.setAnimationAndAngle(new com.ankamagames.boufbowl.resolution.display.animation.AnimationKey(animation),60);
               puppetDisplay=puppetProvider.currentAnimation;
               puppetStage.addChild(puppetDisplay);
               puppetClip=null;puppetBounds=null;
               return "READY";
            }catch(e:Error){return "ERROR: "+e.toString();}
         });
         flash.external.ExternalInterface.addCallback("puppetStatus",function():String {
            if(puppetDisplay==null)return "LOADING";
            puppetClip=puppetFind(puppetDisplay);
            if(puppetClip==null)return "LOADING";
            return flash.utils.getQualifiedClassName(puppetClip)+"|"+puppetClip.currentFrame+"|"+puppetClip.totalFrames+"|"+puppetDisplay.getBounds(puppetDisplay).toString();
         });
         flash.external.ExternalInterface.addCallback("puppetFrame",function(frame:int):String {
            puppetProxy.slowAnimations(0);
            puppetClip.gotoAndStop(frame);
            return String(puppetClip.currentFrame);
         });
         flash.external.ExternalInterface.addCallback("puppetMeasure",function(reset:Boolean):String {
            var b:flash.geom.Rectangle=puppetDisplay.getBounds(puppetDisplay);
            puppetBounds=reset || puppetBounds==null?b:puppetBounds.union(b);
            return puppetBounds.toString();
         });
         flash.external.ExternalInterface.addCallback("puppetPNG",function():String {
            try {
               var scale:Number=640/Math.max(1,puppetBounds.height);
               // A common 600 x 700 canvas leaves room around every complete motion.
               scale=Math.min(scale,540/Math.max(1,puppetBounds.width));
               var bitmap:flash.display.BitmapData=new flash.display.BitmapData(600,700,false,0xf7f7e2);
               bitmap.draw(puppetDisplay,new flash.geom.Matrix(scale,0,0,scale,300-(puppetBounds.x+puppetBounds.width/2)*scale,670-(puppetBounds.y+puppetBounds.height)*scale),null,null,null,true);
               var bytes:flash.utils.ByteArray=com.adobe.images.PNGEncoder.encode(bitmap);
               bitmap.dispose();bytes.position=0;
               var alphabet:String="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
               var out:Array=[];
               while(bytes.bytesAvailable>0){
                  var a:int=bytes.readUnsignedByte();var b:int=bytes.bytesAvailable>0?bytes.readUnsignedByte():-1;var c:int=bytes.bytesAvailable>0?bytes.readUnsignedByte():-1;
                  out.push(alphabet.charAt(a>>2)+alphabet.charAt(((a&3)<<4)|(b<0?0:b>>4))+(b<0?"=":alphabet.charAt(((b&15)<<2)|(c<0?0:c>>6)))+(c<0?"=":alphabet.charAt(c&63)));
               }
               return out.join("");
            }catch(e:Error){return "ERROR: "+e.toString();}
         });
