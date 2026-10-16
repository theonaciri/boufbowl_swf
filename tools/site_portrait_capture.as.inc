         // Temporary export callback, injected only into a separate capture SWF.
         var siteIllustration:flash.display.DisplayObject;
         var siteSprites:as3.collections.ArrayList;
         var siteCharacterKey:String="";
         var siteCharacterInitializations:uint=0;
         flash.external.ExternalInterface.addCallback("siteCharacterInitializations",function():uint{return siteCharacterInitializations;});
         var siteRequest:String="";
         var siteSkin:String="";
         var siteFrames:uint=0;
         var siteStage:Stage=Stage(app.contextInjector.getInstance(Stage));
         siteStage.addEventListener(flash.events.Event.EXIT_FRAME,function(event:flash.events.Event):void {
            if(siteIllustration!=null && siteIllustration.stage!=null)siteFrames++;
         });
         flash.external.ExternalInterface.addCallback("siteStatus",function():String {
            if(siteDomain==null || siteActionDomain==null || siteIllustration==null)return "LOADING";
            var clip:flash.display.MovieClip=Object(siteIllustration).cig_1 as flash.display.MovieClip;
            return siteRequest+"|"+siteFrames+"|"+(clip==null ? "" : clip.currentLabel)+"|"+(clip==null ? "" : flash.utils.getQualifiedClassName(clip));
         });
         var siteDomain:flash.system.ApplicationDomain;
         var siteActionDomain:flash.system.ApplicationDomain;
         var siteLoader:flash.display.Loader=new flash.display.Loader();
         var siteConfig:IBoufbowlConfig=app.contextInjector.getInstance(IBoufbowlConfig);
         siteLoader.contentLoaderInfo.addEventListener(flash.events.Event.COMPLETE,function(event:flash.events.Event):void {
            siteDomain=siteLoader.contentLoaderInfo.applicationDomain;
         });
         siteLoader.load(new flash.net.URLRequest(siteConfig.cutscenesBoufbowlerRepositoryFile),new flash.system.LoaderContext(false,new flash.system.ApplicationDomain(flash.system.ApplicationDomain.currentDomain)));
         var siteActionLoader:flash.display.Loader=new flash.display.Loader();
         siteActionLoader.contentLoaderInfo.addEventListener(flash.events.Event.COMPLETE,function(event:flash.events.Event):void {
            siteActionDomain=siteActionLoader.contentLoaderInfo.applicationDomain;
         });
         siteActionLoader.load(new flash.net.URLRequest("../assets/artworks/cutscene-illustration.swf"),new flash.system.LoaderContext(false,new flash.system.ApplicationDomain(flash.system.ApplicationDomain.currentDomain)));
         flash.external.ExternalInterface.addCallback("siteRender",function(cls:int,gender:int,hero:int,pose:String,hair:uint,skin:uint,eyes:uint,request:String):String {
            try {
               if(siteDomain==null || siteActionDomain==null)return "LOADING";
               if(siteIllustration!=null && siteIllustration.parent!=null)siteIllustration.parent.removeChild(siteIllustration);
               var action:Boolean=pose.indexOf("action:")==0;
               var symbol:String=pose=="alternate" || action ? "BoufbowlerIllustrationDefaultPosing" : pose;
               var C:Class=siteDomain.getDefinition(symbol) as Class;
               var illustration:com.ankamagames.boufbowl.resolution.display.cutscene.illustration.BoufbowlerIllustration=new C();
               if(pose=="alternate" || action) {
                  var groupClass:Class=action ? siteActionDomain.getDefinition(pose.substr(7)) as Class : siteDomain.getDefinition("boufbowler1_posing_11") as Class;
                  var old:flash.display.DisplayObject=Object(illustration).cig_1;
                  var group:flash.display.DisplayObject=new groupClass();
                  group.name="cig_1";group.transform.matrix=old.transform.matrix;
                  illustration.removeChild(old);Object(illustration).cig_1=group;illustration.addChild(group);
               }
               var characterKey:String=cls+":"+gender+":"+hero+":"+hair+":"+skin+":"+eyes;
               if(siteCharacterKey!=characterKey) {
               siteCharacterInitializations++;
               var colors:as3.collections.Map=new as3.collections.Map();
               colors.addItem(1,Color3.fromRgbUInt(hair));
               colors.addItem(2,Color3.fromRgbUInt(eyes));
               colors.addItem(3,Color3.fromRgbUInt(skin));
               colors.addItem(4,Color3.fromRgbUInt(0x3578cf));
               colors.addItem(5,Color3.fromRgbUInt(0x3578cf));
               var sprites:as3.collections.ArrayList=new as3.collections.ArrayList();
               sprites.addItem(new com.ankamagames.boufbowl.client.club.view.ClubIllustrationBoufbowlerSprite(cls,gender,hero,colors));
               siteSprites=sprites;siteCharacterKey=characterKey;
               }
               illustration.initFrom(siteSprites,null);
               var st:Stage=Stage(app.contextInjector.getInstance(Stage));
               while(st.numChildren>0)st.removeChildAt(st.numChildren-1);
               siteRequest=request;siteSkin="cg_"+(hero!=0 ? hero : cls*10+gender);siteFrames=0;
               st.addChild(illustration);siteIllustration=illustration;
               return "READY";
            }catch(e:Error){return "ERROR: "+e.toString();}
         });
         flash.external.ExternalInterface.addCallback("sitePNG",function():String {
            try {
               var bounds:flash.geom.Rectangle=siteIllustration.getBounds(siteIllustration);
               var scale:Number=1000/Math.max(1,bounds.height);
               var width:int=Math.ceil(bounds.width*scale)+80;
               var bitmap:flash.display.BitmapData=new flash.display.BitmapData(width,1080,true,0);
               bitmap.draw(siteIllustration,new flash.geom.Matrix(scale,0,0,scale,40-bounds.x*scale,40-bounds.y*scale),null,null,null,true);
               var bytes:flash.utils.ByteArray=com.adobe.images.PNGEncoder.encode(bitmap);
               bitmap.dispose();bytes.position=0;
               var alphabet:String="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
               var out:Array=[];
               while(bytes.bytesAvailable>0) {
                  var a:int=bytes.readUnsignedByte();
                  var b:int=bytes.bytesAvailable>0?bytes.readUnsignedByte():-1;
                  var c:int=bytes.bytesAvailable>0?bytes.readUnsignedByte():-1;
                  out.push(alphabet.charAt(a>>2)+alphabet.charAt(((a&3)<<4)|(b<0?0:b>>4))+(b<0?"=":alphabet.charAt(((b&15)<<2)|(c<0?0:c>>6)))+(c<0?"=":alphabet.charAt(c&63)));
               }
               return out.join("");
            }catch(e:Error){return "ERROR: "+e.toString();}
         });
         flash.external.ExternalInterface.addCallback("sitePreview",function():String {
            var bounds:flash.geom.Rectangle=siteIllustration.getBounds(siteIllustration);
            siteIllustration.scaleX=siteIllustration.scaleY=500/Math.max(1,bounds.height);
            siteIllustration.x=512-(bounds.x+bounds.width/2)*siteIllustration.scaleX;
            siteIllustration.y=35-bounds.y*siteIllustration.scaleY;
            siteFrames=0;
            return bounds.toString();
         });
