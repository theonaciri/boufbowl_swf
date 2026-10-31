package away3d.core.session
{
   import away3d.arcane;
   import away3d.containers.*;
   import away3d.core.clip.*;
   import away3d.events.*;
   import flash.display.*;
   import flash.geom.*;

   use namespace arcane;

   public class SpriteSession extends AbstractSession
   {

      private var _container:Sprite;

      private var _clip:Clipping;

      private var _childIndex:int = 0;

      public var cacheAsBitmap:Boolean;

      public function SpriteSession()
      {
         super();
      }

      override protected function onSessionUpdate(param1:SessionEvent) : void
      {
         super.onSessionUpdate(param1);
         this.cacheAsBitmap = false;
      }

      override public function getContainer(param1:View3D) : DisplayObject
      {
         if(!_containers[param1])
         {
            return _containers[param1] = new Sprite();
         }
         return _containers[param1];
      }

      override public function addDisplayObject(displayObject:DisplayObject) : void
      {
         this.placeChild(displayObject);
         displayObject.visible = true;
         layer = null;
         _level = -1;
         _layerDirty = true;
      }

      override protected function createSprite(parentSprite:Sprite = null) : Sprite
      {
         if(_spriteStore.length)
         {
            _spriteActive.push(_sprite = _spriteStore.pop());
         }
         else
         {
            _spriteActive.push(_sprite = new Sprite());
         }
         if(parentSprite)
         {
            parentSprite.addChild(_sprite);
         }
         else
         {
            this.placeChild(_sprite);
            layer = _sprite;
         }
         _layerDirty = true;
         return _sprite;
      }

      override protected function createLayer() : void
      {
         if(_shapeStore.length)
         {
            _shapeActive.push(_shape = _shapeStore.pop());
         }
         else
         {
            _shapeActive.push(_shape = new Shape());
         }
         layer = _shape;
         graphics = _shape.graphics;
         this.placeChild(_shape);
         _layerDirty = false;
         _level = -1;
      }

      override public function clear(view:View3D) : void
      {
         super.clear(view);
         this._container = this.getContainer(view) as Sprite;
         if(updated)
         {
            layer = this._container;
            graphics = this._container.graphics;
            if(this == view.session)
            {
               this._clip = view.screenClipping;
               this._container.scrollRect = new Rectangle(this._clip.minX - 1,this._clip.minY - 1,this._clip.maxX - this._clip.minX + 2,this._clip.maxY - this._clip.minY + 2);
               this._container.x = this._clip.minX - 1;
               this._container.y = this._clip.minY - 1;
            }
            this._container.cacheAsBitmap = false;
            this.clearBrowserGraphics(graphics);
            this._childIndex = 0;
         }
         else
         {
            this._container.cacheAsBitmap = this.cacheAsBitmap;
         }
         if(Boolean(filters) && Boolean(filters.length) || Boolean(this._container.filters) && Boolean(this._container.filters.length))
         {
            this._container.filters = filters;
         }
         this._container.alpha = alpha;
         this._container.blendMode = blendMode || BlendMode.NORMAL;
      }

      // Keep display objects on stage while reconciling the painter's order.
      // Removing every child on every draw restarts stage lifecycle work for
      // the entire character tree even when only its world position changed.
      private function placeChild(displayObject:DisplayObject) : void
      {
         var previousIndex:int = displayObject.parent == this._container ?
            this._container.getChildIndex(displayObject) : -1;
         if(previousIndex >= 0 && previousIndex < this._childIndex)
         {
            // Drawing an object twice has the same last-draw-wins order as addChild.
            if(previousIndex != this._childIndex - 1)
               this._container.setChildIndex(displayObject,this._childIndex - 1);
            return;
         }
         if(previousIndex < 0)
            this._container.addChildAt(displayObject,this._childIndex);
         else if(previousIndex != this._childIndex)
            this._container.setChildIndex(displayObject,this._childIndex);
         this._childIndex++;
      }

      override public function render(view:View3D) : void
      {
         super.render(view);
         if(updated)
         {
            while(this._container.numChildren > this._childIndex)
               this._container.removeChildAt(this._container.numChildren - 1);
         }
      }

      override public function clone() : AbstractSession
      {
         return new SpriteSession();
      }
   }
}
