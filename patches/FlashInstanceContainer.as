package com.ankamagames.xgaming.ui.components
{
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.display.DisplayListUtils;
   import flash.display.MovieClip;
   import flash.display.Bitmap;
   import flash.display.BitmapData;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.Sprite;
   import flash.display.Shape;
   import flash.events.Event;
   import flash.geom.Matrix;
   import flash.geom.Point;
   import flash.geom.Rectangle;
   import flash.system.Capabilities;
   import flash.utils.Dictionary;
   import flash.text.TextField;
   import flash.text.TextFormatAlign;
   import flashx.textLayout.formats.TextAlign;

   public class FlashInstanceContainer extends MovieClip
   {

      public function FlashInstanceContainer()
      {
         super();
         this.initFlashInstances();
         // Ruffle currently stores scale9Grid but does not apply it when drawing.
         // Keep Flash standalone/AIR artwork on the native vector path.
         if(Capabilities.playerType == "PlugIn")
         {
            addEventListener(Event.ADDED_TO_STAGE,this.startBrowserArtwork,false,0,true);
            addEventListener(Event.REMOVED_FROM_STAGE,this.stopBrowserArtwork,false,0,true);
            if(stage != null) this.startBrowserArtwork();
         }
      }

      private static var browserSlices:Dictionary = new Dictionary(true);
      private var browserArtworkInitialized:Boolean = false;
      private var browserArtworkHosts:Array = [];

      private function startBrowserArtwork(event:Event = null) : void
      {
         if(!this.browserArtworkInitialized || this.browserArtworkHosts.length > 0)
            addEventListener(Event.ENTER_FRAME,this.updateBrowserArtwork,false,0,true);
      }

      private function stopBrowserArtwork(event:Event) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.updateBrowserArtwork);
      }

      private function updateBrowserArtwork(event:Event) : void
      {
         if(!this.browserArtworkInitialized)
         {
            this.browserArtworkInitialized=true;
            repairBrowserArtwork(this,this.browserArtworkHosts);
            if(this.browserArtworkHosts.length == 0)
               removeEventListener(Event.ENTER_FRAME,this.updateBrowserArtwork);
         }
         for each(var host:DisplayObjectContainer in this.browserArtworkHosts)
         {
            var slices:Object=browserSlices[host];
            if(host.scaleX != slices.horizontal || host.scaleY != slices.vertical)
               layoutBrowserSlices(host,slices);
         }
      }

      private static function staticArtwork(object:DisplayObject) : Boolean
      {
         // ColorableZone shapes are live channel/team indicators, not artwork.
         if(object is ColorableZone) return false;
         if(object is FlashInstanceContainer) return false;
         if(object is Shape || object is Bitmap) return true;
         if(!(object is Sprite)) return false;
         if(object is MovieClip && MovieClip(object).totalFrames != 1) return false;
         var container:DisplayObjectContainer = DisplayObjectContainer(object);
         for(var index:int=0;index<container.numChildren;index++)
            if(!staticArtwork(container.getChildAt(index))) return false;
         return true;
      }

      private static function repairBrowserArtwork(container:DisplayObjectContainer, hosts:Array) : void
      {
         for(var index:int=0;index<container.numChildren;index++)
         {
            var child:DisplayObject = container.getChildAt(index);
            // Nested components maintain their own artwork. Scanning them here
            // registers the same backgrounds with every ancestor each frame.
            if(child is FlashInstanceContainer) continue;
            if(!(child is DisplayObjectContainer)) continue;
            var host:DisplayObjectContainer = DisplayObjectContainer(child);
            if((browserSlices[host] != null || staticArtwork(host)) && repairBrowserSkin(host))
               hosts.push(host);
            else
               repairBrowserArtwork(host,hosts);
         }
      }

      // Also used for detached popup backgrounds and the slider's track skin.
      // Only explicitly opted-in timeline skins may snapshot their current frame.
      public static function repairBrowserSkin(host:DisplayObjectContainer, timeline:Boolean = false) : Boolean
      {
         if(Capabilities.playerType != "PlugIn") return false;
         var grid:Rectangle=host.scale9Grid;
         if(grid == null || grid.width <= 0 || grid.height <= 0 || host.rotation != 0 || host.scaleX <= 0 || host.scaleY <= 0)
            return false;
         var frame:int=host is MovieClip ? MovieClip(host).currentFrame : 1;
         var slices:Object=browserSlices[host];
         if(slices != null && slices.frame != frame)
         {
            for each(var previous:Object in slices.originals)
               if(previous.child.parent == host) previous.child.visible=previous.visible;
            for each(var oldTile:Bitmap in slices.tiles)
               if(oldTile != null)
               {
                  if(oldTile.parent == host) host.removeChild(oldTile);
                  oldTile.bitmapData.dispose();
               }
            if(slices.rendered != null)
            {
               if(slices.rendered.parent == host) host.removeChild(slices.rendered);
               slices.rendered.bitmapData.dispose();
            }
            delete browserSlices[host];
            slices=null;
         }
         if(slices == null)
         {
            if(host is MovieClip && MovieClip(host).totalFrames != 1 && !timeline) return false;
            for(var index:int=0;index<host.numChildren;index++)
               if(!staticArtwork(host.getChildAt(index))) return false;
            var bounds:Rectangle=host.getBounds(host);
            var content:Rectangle=host.getRect(host);
            if(content.width <= 0 || content.height <= 0) content=bounds.clone();
            if(bounds.width <= 0 || bounds.height <= 0 || bounds.width > 1024 || bounds.height > 600
               || grid.left < bounds.left || grid.right > bounds.right
               || grid.top < bounds.top || grid.bottom > bounds.bottom) return false;
            var texture:BitmapData=new BitmapData(Math.ceil(bounds.width*2),Math.ceil(bounds.height*2),true,0);
            try
            {
               texture.draw(host,new Matrix(2,0,0,2,-bounds.x*2,-bounds.y*2),null,null,null,true);
            }
            catch(error:Error)
            {
               // Basic Ruffle renderers cannot draw to a bitmap. Keep the
               // vector skin instead of aborting initialization every frame.
               texture.dispose();
               return false;
            }
            var columns:Array=[bounds.left,grid.left,grid.right,bounds.right];
            var rows:Array=[bounds.top,grid.top,grid.bottom,bounds.bottom];
            var tiles:Array=[];
            var originals:Array=[];
            var originalCount:int=host.numChildren;
            for(var oldIndex:int=0;oldIndex<originalCount;oldIndex++)
            {
               var original:DisplayObject=host.getChildAt(oldIndex);
               originals.push({child:original,visible:original.visible});
               original.visible=false;
            }
            for(var row:int=0;row<3;row++)
               for(var column:int=0;column<3;column++)
               {
                  var pixelLeft:int=Math.round((columns[column]-bounds.x)*2);
                  var pixelTop:int=Math.round((rows[row]-bounds.y)*2);
                  var rect:Rectangle=new Rectangle(pixelLeft,pixelTop,
                     Math.round((columns[column+1]-bounds.x)*2)-pixelLeft,
                     Math.round((rows[row+1]-bounds.y)*2)-pixelTop);
                  if(rect.width <= 0 || rect.height <= 0) { tiles.push(null); continue; }
                  var pixels:BitmapData=new BitmapData(rect.width,rect.height,true,0);
                  pixels.copyPixels(texture,rect,new Point());
                  var tile:Bitmap=new Bitmap(pixels,"auto",true);
                  tiles.push(tile);
               }
            texture.dispose();
            slices={bounds:bounds,content:content,grid:grid,tiles:tiles,originals:originals,frame:frame,rendered:null};
            browserSlices[host]=slices;
         }
         if(host.scaleX != slices.horizontal || host.scaleY != slices.vertical)
            layoutBrowserSlices(host,slices);
         return true;
      }

      private static function layoutBrowserSlices(host:DisplayObjectContainer, slices:Object) : void
      {
         var bounds:Rectangle = slices.bounds;
         var grid:Rectangle = slices.grid;
         var horizontal:Number = host.scaleX;
         var vertical:Number = host.scaleY;
         if(horizontal <= 0 || vertical <= 0) return;
         slices.horizontal=horizontal;
         slices.vertical=vertical;
         var left:Number = grid.left-bounds.left;
         var right:Number = bounds.right-grid.right;
         var top:Number = grid.top-bounds.top;
         var bottom:Number = bounds.bottom-grid.bottom;
         // Flash scales the fill rectangle, then adds the unscaled stroke
         // margins. Scaling getBounds() instead expands thick chat borders.
         var content:Rectangle = slices.content;
         var x:Number = content.x*horizontal-(content.left-bounds.left);
         var y:Number = content.y*vertical-(content.top-bounds.top);
         var width:Number = Math.max(content.width*horizontal+bounds.width-content.width,left+right);
         var height:Number = Math.max(content.height*vertical+bounds.height-content.height,top+bottom);
         var columns:Array = [x,x+left,x+width-right,x+width];
         var rows:Array = [y,y+top,y+height-bottom,y+height];
         // Compose onto one surface with shared integer pixel edges. Separate
         // smoothed quads leave hairline gaps at fractional device scales.
         var resolution:Number = Math.min(2,2048 / width,2048 / height);
         var pixels:BitmapData = new BitmapData(Math.max(1,Math.ceil(width * resolution)),
            Math.max(1,Math.ceil(height * resolution)),true,0);
         for(var row:int=0;row<3;row++)
         {
            for(var column:int=0;column<3;column++)
            {
               var tile:Bitmap = slices.tiles[row*3+column];
               if(tile == null) continue;
               var pixelLeft:int = Math.round((columns[column] - x) * resolution);
               var pixelTop:int = Math.round((rows[row] - y) * resolution);
               var pixelWidth:int = Math.round((columns[column+1] - x) * resolution) - pixelLeft;
               var pixelHeight:int = Math.round((rows[row+1] - y) * resolution) - pixelTop;
               if(pixelWidth <= 0 || pixelHeight <= 0) continue;
               var matrix:Matrix = new Matrix(pixelWidth / tile.bitmapData.width,0,0,
                  pixelHeight / tile.bitmapData.height,pixelLeft,pixelTop);
               pixels.draw(tile.bitmapData,matrix,null,null,
                  new Rectangle(pixelLeft,pixelTop,pixelWidth,pixelHeight),true);
            }
         }
         if(slices.rendered == null)
         {
            slices.rendered = new Bitmap(pixels,"auto",true);
            host.addChild(slices.rendered);
         }
         else
         {
            var previous:BitmapData = slices.rendered.bitmapData;
            slices.rendered.bitmapData = pixels;
            previous.dispose();
         }
         slices.rendered.x = x / horizontal;
         slices.rendered.y = y / vertical;
         slices.rendered.width = width / horizontal;
         slices.rendered.height = height / vertical;
      }

      protected function initFlashInstances() : void
      {
      }

      final protected function getFlashInstance(param1:String, param2:Class, param3:Boolean = true) : *
      {
         return DisplayListUtils.getFlashInstance(this,param1,param2,param3);
      }

      protected function textFieldToTextZone(param1:String) : TextZone
      {
         var _loc2_:TextField = this.getFlashInstance(param1,TextField);
         var _loc3_:TextZone = new TextZone();
         if(_loc2_.defaultTextFormat.font != null && _loc2_.defaultTextFormat.font.length > 0)
         {
            _loc3_.defaultFontFamily = _loc2_.defaultTextFormat.font + "CFF";
         }
         if(_loc2_.defaultTextFormat.size != null)
         {
            _loc3_.defaultFontSize = int(_loc2_.defaultTextFormat.size);
         }
         if(_loc2_.defaultTextFormat.color != null)
         {
            _loc3_.defaultTextColor = Color3.fromRgbUInt(uint(_loc2_.defaultTextFormat.color));
         }
         _loc3_.defaultTextAlign = this.toTextAlign(_loc2_.defaultTextFormat.align);
         _loc3_.setSize(_loc2_.width,_loc2_.height);
         _loc3_.x = Math.floor(_loc2_.x);
         _loc3_.y = Math.floor(_loc2_.y);
         _loc3_.setContent(_loc2_.text);
         var _loc4_:int = _loc2_.parent.getChildIndex(_loc2_);
         _loc2_.parent.addChildAt(_loc3_,_loc4_);
         _loc2_.parent.removeChild(_loc2_);
         return _loc3_;
      }

      private function toTextAlign(param1:String) : String
      {
         switch(param1)
         {
            case TextFormatAlign.LEFT:
               return TextAlign.LEFT;
            case TextFormatAlign.RIGHT:
               return TextAlign.RIGHT;
            case TextFormatAlign.CENTER:
               return TextAlign.CENTER;
            case TextFormatAlign.JUSTIFY:
               return TextAlign.JUSTIFY;
            default:
               return null;
         }
      }
   }
}

