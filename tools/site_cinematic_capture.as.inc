         // Export-only player for the original full-screen illustration movies.
         var cineDomain:flash.system.ApplicationDomain;
         var cineMovie:flash.display.MovieClip;
         var cineAges:flash.utils.Dictionary=new flash.utils.Dictionary(true);
         var cineActors:Array=[];
         var cineStage:Stage=Stage(app.contextInjector.getInstance(Stage));
         var cineLoader:flash.display.Loader=new flash.display.Loader();
         cineLoader.contentLoaderInfo.addEventListener(flash.events.Event.COMPLETE,function(event:flash.events.Event):void {
            cineDomain=cineLoader.contentLoaderInfo.applicationDomain;
         });
         cineLoader.load(new flash.net.URLRequest("../assets/artworks/cutscene-illustration.swf"),new flash.system.LoaderContext(false,new flash.system.ApplicationDomain(flash.system.ApplicationDomain.currentDomain)));
         var cineFreeze:Function=function(container:flash.display.DisplayObjectContainer,frame:int):void {
            // Native skin/color groups select their own labelled frames. Preserve their entire subtree.
            if(container is com.ankamagames.boufbowl.resolution.display.cutscene.illustration.ColorizableIllustrationGroup){
               flash.display.MovieClip(container).stop();return;
            }
            if(container is flash.display.MovieClip){
               var mc:flash.display.MovieClip=container as flash.display.MovieClip;
               if(container!=cineMovie && !(container is com.ankamagames.boufbowl.resolution.display.cutscene.illustration.BoufbowlerIllustrationGroup) && mc.totalFrames>1){
                  if(cineAges[mc]==null)cineAges[mc]=frame;
                  mc.gotoAndStop((frame-int(cineAges[mc]))%mc.totalFrames+1);
               }
               mc.stop();
            }
            for(var i:int=0;i<container.numChildren;i++)if(container.getChildAt(i) is flash.display.DisplayObjectContainer)cineFreeze(container.getChildAt(i),frame);
         };
         flash.external.ExternalInterface.addCallback("cinemaCreate",function(symbol:String,actors:String):String {
            try {
               if(cineDomain==null)return "LOADING";
               while(cineStage.numChildren>0)cineStage.removeChildAt(cineStage.numChildren-1);
               cineAges=new flash.utils.Dictionary(true);
               var C:Class=cineDomain.getDefinition(symbol) as Class;
               var movie:com.ankamagames.boufbowl.resolution.display.cutscene.illustration.BoufbowlerIllustration=new C();
               var cast:Array=com.adobe.serialization.json.JSON.decode(actors);
               var sprites:as3.collections.ArrayList=new as3.collections.ArrayList();
               for each(var actor:Object in cast){
                  var colors:as3.collections.Map=new as3.collections.Map();
                  colors.addItem(1,Color3.fromRgbUInt(uint(actor.hair)));colors.addItem(2,Color3.fromRgbUInt(uint(actor.eyes)));colors.addItem(3,Color3.fromRgbUInt(uint(actor.skin)));
                  colors.addItem(4,Color3.fromRgbUInt(uint(actor.team)));colors.addItem(5,Color3.fromRgbUInt(uint(actor.team)));
                  sprites.addItem(new com.ankamagames.boufbowl.client.club.view.ClubIllustrationBoufbowlerSprite(actor.cls,actor.gender,actor.hero,colors));
               }
               movie.initFrom(sprites,null);movie.stop();movie.x=512;movie.y=300;
               cineStage.frameRate=25;cineStage.addChild(movie);cineMovie=movie;
               return String(movie.totalFrames);
            }catch(e:Error){return "ERROR: "+e.toString();}
         });
         flash.external.ExternalInterface.addCallback("cinemaFrame",function(frame:int):String {
            try{cineMovie.gotoAndStop(frame);return String(cineMovie.currentFrame);}catch(e:Error){return "ERROR: "+e.toString();}
         });
         flash.external.ExternalInterface.addCallback("cinemaFreeze",function(frame:int):String {
            try{cineFreeze(cineMovie,frame);return "READY";}catch(e:Error){return "ERROR: "+e.toString();}
         });
         flash.external.ExternalInterface.addCallback("cinemaGroups",function():String {
            var result:Array=[];
            var walk:Function=function(c:flash.display.DisplayObjectContainer):void{
               if(c is com.ankamagames.boufbowl.resolution.display.cutscene.illustration.BoufbowlerIllustrationGroup){var m:flash.display.MovieClip=c as flash.display.MovieClip;result.push({name:m.name,label:m.currentLabel,visible:m.visible});}
               for(var i:int=0;i<c.numChildren;i++)if(c.getChildAt(i) is flash.display.DisplayObjectContainer)walk(c.getChildAt(i));
            };walk(cineMovie);return com.adobe.serialization.json.JSON.encode(result);
         });
