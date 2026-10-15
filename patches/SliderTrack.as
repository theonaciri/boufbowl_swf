package com.ankamagames.boufbowl.client.ui
{
   import com.ankamagames.xgaming.ui.components.BaseComponent;
   import flash.display.Shape;
   import flash.events.Event;
   import flash.system.Capabilities;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol756")]
   public dynamic class SliderTrack extends BaseComponent
   {
      // Original symbol 755 paths. Draw their end caps as vectors so the
      // native hairline outline is not weakened by bitmap supersampling.
      private static var browserPaths:Array = [
         {commands:Vector.<int>([1,2,2,2,2,2,2,2,2,2,2,2,2 ]),
          data:Vector.<Number>([11.35,6.35,6.65,6.35,5.9,6.35,1.05,6.35,1.05,4.1,1.05,3.45,1.05,1,5.9,1,6.65,1,11.35,1,11.35,3.45,11.35,4.1,11.35,6.35]),
          color:0xa5a474, alpha:1, stroke:-1},
         {commands:Vector.<int>([1,2,2,2,2,2,3,2,2,3,3,2,2,2,2,2,2,3,3,3,3,2,2,2,2,3,3,2,1,2,2,3,3,3,3,2,2,2,3,3,3,3,2 ]),
          data:Vector.<Number>([11.25,3.45,11.55,4.1,11.75,4.75,11.85,4.15,11.85,3.5,11.8,3,11.65,2.05,11.2,1.4,11.15,1.35,10.9,1.1,10.6,0.8,10.3,0.8,9.85,0.8,9.5,1.25,9.3,1.7,8.9,1.65,8.55,1.6,6.65,1.6,5.9,1.6,4.15,1.6,3,1.6,2.25,2.25,1.45,2.85,1.45,3.8,1.45,4.65,2.25,5.3,3,5.9,4.15,5.9,5.9,5.9,6.65,5.9,8.55,5.9,8.9,5.9,9.8,5.8,10.45,5.3,11.25,4.65,11.25,3.8,11.25,3.45,5.9,0,6.65,0,9.85,0,11,0,11.85,1.1,12.65,2.2,12.65,3.75,12.65,5.3,11.85,6.35,11,7.45,9.85,7.45,6.65,7.45,5.9,7.45,2.8,7.45,1.65,7.45,0.85,6.35,0,5.3,0,3.75,0,2.2,0.85,1.1,1.65,0,2.8,0,5.9,0]),
          color:0xc8298f, alpha:1, stroke:-1},
         {commands:Vector.<int>([1,2,3,3,2,2,2,2,3,3,3,3,2,2,2,2,2 ]),
          data:Vector.<Number>([11.25,3.45,11.25,3.8,11.25,4.65,10.45,5.3,9.8,5.8,8.9,5.9,8.55,5.9,6.65,5.9,5.9,5.9,4.15,5.9,3,5.9,2.25,5.3,1.45,4.65,1.45,3.8,1.45,2.85,2.25,2.25,3,1.6,4.15,1.6,5.9,1.6,6.65,1.6,8.55,1.6,8.9,1.65,9.3,1.7]),
          color:0x660030, alpha:0.4, stroke:1.0},
         {commands:Vector.<int>([1,2,3,3,3,3,2,2,2,3,3,3,3,2,2,2 ]),
          data:Vector.<Number>([5.9,0,2.8,0,1.65,0,0.85,1.1,0,2.2,0,3.75,0,5.3,0.85,6.35,1.65,7.45,2.8,7.45,5.9,7.45,6.65,7.45,9.85,7.45,11,7.45,11.85,6.35,12.65,5.3,12.65,3.75,12.65,2.2,11.85,1.1,11,0,9.85,0,6.65,0,5.9,0,5.9,0]),
          color:0x660030, alpha:0.4, stroke:0.05},
         {commands:Vector.<int>([1,2,2,3,3,2,2,3,3,2,2,3,2,2,2,2,2 ]),
          data:Vector.<Number>([11.25,3.45,11.1,3.4,10.3,3.9,9.85,3.9,9.5,3.4,9.15,2.95,9.15,2.35,9.3,1.7,9.5,1.25,9.85,0.8,10.3,0.8,10.6,0.8,10.9,1.1,11.15,1.35,11.2,1.4,11.65,2.05,11.8,3,11.85,3.5,11.85,4.15,11.75,4.75,11.55,4.1,11.25,3.45]),
          color:0xffffff, alpha:1, stroke:-1}
      ];
      private var browserShape:Shape;
      private var browserFrame:int = -1;
      private var browserScaleX:Number;
      private var browserScaleY:Number;
      
      public function SliderTrack()
      {
         super();
         addFrameScript(0,this.frame1,1,this.frame2,2,this.frame3,3,this.frame4);
         if(Capabilities.playerType == "PlugIn")
         {
            addEventListener(Event.ADDED_TO_STAGE,this.startBrowserTrack,false,0,true);
            addEventListener(Event.REMOVED_FROM_STAGE,this.stopBrowserTrack,false,0,true);
            if(stage != null) this.startBrowserTrack();
         }
      }

      private function startBrowserTrack(event:Event = null) : void
      {
         addEventListener(Event.ENTER_FRAME,this.browserTrackArtwork,false,0,true);
      }

      private function stopBrowserTrack(event:Event) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.browserTrackArtwork);
      }
      
      private function browserTrackArtwork(event:Event) : void
      {
         if(currentFrame == this.browserFrame && scaleX == this.browserScaleX && scaleY == this.browserScaleY) return;
         if(scaleX <= 0 || scaleY <= 0) return;
         if(this.browserShape == null) this.browserShape=new Shape();
         for(var child:int=0;child<numChildren;child++)
            if(getChildAt(child) != this.browserShape) getChildAt(child).visible=false;
         if(this.browserShape.parent != this) addChild(this.browserShape);
         this.browserShape.scaleX=1/scaleX;
         this.browserShape.scaleY=1/scaleY;
         var width:Number=Math.max(12,12.65*scaleX);
         var height:Number=Math.max(6.9,7.45*scaleY);
         this.browserShape.graphics.clear();
         for each(var path:Object in browserPaths)
         {
            var coordinates:Vector.<Number> = new Vector.<Number>();
            for(var index:int=0;index<path.data.length;index+=2)
            {
               coordinates.push(this.browserCoordinate(path.data[index],5.95,6.6,12.65,width));
               coordinates.push(this.browserCoordinate(path.data[index+1],3.5,4.05,7.45,height));
            }
            if(path.stroke < 0)
            {
               this.browserShape.graphics.lineStyle();
               this.browserShape.graphics.beginFill(path.color,path.alpha);
            }
            else this.browserShape.graphics.lineStyle(path.stroke,path.color,path.alpha);
            var position:int=0;
            for each(var command:int in path.commands)
            {
               if(command == 1) this.browserShape.graphics.moveTo(coordinates[position++],coordinates[position++]);
               else if(command == 2) this.browserShape.graphics.lineTo(coordinates[position++],coordinates[position++]);
               else this.browserShape.graphics.curveTo(coordinates[position++],coordinates[position++],coordinates[position++],coordinates[position++]);
            }
            if(path.stroke < 0) this.browserShape.graphics.endFill();
         }
         this.browserFrame=currentFrame;
         this.browserScaleX=scaleX;
         this.browserScaleY=scaleY;
      }

      private function browserCoordinate(value:Number, start:Number, end:Number, original:Number, target:Number) : Number
      {
         if(value <= start) return value;
         if(value >= end) return target-original+value;
         return start+(value-start)*(target-original+end-start)/(end-start);
      }

      internal function frame1() : *
      {
         stop();
      }
      
      internal function frame2() : *
      {
         stop();
      }
      
      internal function frame3() : *
      {
         stop();
      }
      
      internal function frame4() : *
      {
         stop();
      }
   }
}

