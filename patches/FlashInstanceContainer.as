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
            addEventListener(Event.ENTER_FRAME,this.updateBrowserArtwork,false,0,true);
      }

      private static var browserSlices:Dictionary = new Dictionary(true);
      private var browserArtworkInitialized:Boolean = false;
      private var browserArtworkHosts:Array = [];

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
            delete browserSlices[host];
            slices=null;
         }
         if(slices == null)
         {
            if(host is MovieClip && MovieClip(host).totalFrames != 1 && !timeline) return false;
            for(var index:int=0;index<host.numChildren;index++)
               if(!staticArtwork(host.getChildAt(index))) return false;
            var bounds:Rectangle=host.getBounds(host);
            if(bounds.width <= 0 || bounds.height <= 0 || bounds.width > 1024 || bounds.height > 600
               || grid.left < bounds.left || grid.right > bounds.right
               || grid.top < bounds.top || grid.bottom > bounds.bottom) return false;
            var texture:BitmapData=new BitmapData(Math.ceil(bounds.width*2),Math.ceil(bounds.height*2),true,0);
            texture.draw(host,new Matrix(2,0,0,2,-bounds.x*2,-bounds.y*2),null,null,null,true);
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
                  var rect:Rectangle=new Rectangle(Math.round((columns[column]-bounds.x)*2),Math.round((rows[row]-bounds.y)*2),
                     Math.round((columns[column+1]-columns[column])*2),Math.round((rows[row+1]-rows[row])*2));
                  if(rect.width <= 0 || rect.height <= 0) { tiles.push(null); continue; }
                  var pixels:BitmapData=new BitmapData(rect.width,rect.height,true,0);
                  pixels.copyPixels(texture,rect,new Point());
                  var tile:Bitmap=new Bitmap(pixels,"auto",true);
                  tiles.push(tile);host.addChild(tile);
               }
            texture.dispose();
            slices={bounds:bounds,grid:grid,tiles:tiles,originals:originals,frame:frame};
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
         var width:Number = Math.max(bounds.width*horizontal,left+right);
         var height:Number = Math.max(bounds.height*vertical,top+bottom);
         var columns:Array = [bounds.x*horizontal,bounds.x*horizontal+left,bounds.x*horizontal+width-right,bounds.x*horizontal+width];
         var rows:Array = [bounds.y*vertical,bounds.y*vertical+top,bounds.y*vertical+height-bottom,bounds.y*vertical+height];
         for(var row:int=0;row<3;row++)
         {
            for(var column:int=0;column<3;column++)
            {
               var tile:Bitmap = slices.tiles[row*3+column];
               if(tile == null) continue;
               tile.x=columns[column]/horizontal;
               tile.y=rows[row]/vertical;
               tile.width=(columns[column+1]-columns[column])/horizontal;
               tile.height=(rows[row+1]-rows[row])/vertical;
            }
         }
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

