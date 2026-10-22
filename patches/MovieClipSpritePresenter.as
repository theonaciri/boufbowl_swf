package com.ankamagames.boufbowl.resolution.display.presenter
{
   import away3d.core.base.Geometry;
   import away3d.core.base.Vertex;
   import away3d.sprites.MovieClipSprite;
   import away3d.sprites.Sprite3D;
   import com.ankamagames.xgaming.utils.math.geom.Point3;
   import flash.display.Sprite;

   public class MovieClipSpritePresenter implements ISpritePresenter
   {

      private var _movieClipSprite:MovieClipSprite;

      private var _visible:Boolean;

      private var _savedParent:Geometry;

      public function MovieClipSpritePresenter(param1:Number)
      {
         super();
         this._movieClipSprite = new MovieClipSprite(null,"none",param1,true);
         this._visible = true;
         this._savedParent = null;
      }

      public function get visible() : Boolean
      {
         return this._visible;
      }

      public function set visible(param1:Boolean) : void
      {
         if(this._visible == param1)
         {
            return;
         }
         this._visible = param1;
         if(this._visible && this._savedParent != null)
         {
            this._savedParent.addSprite(this._movieClipSprite);
            this._savedParent = null;
            this.invalidate();
         }
         else if(!this._visible && this._savedParent == null && this._movieClipSprite.parent != null)
         {
            this._savedParent = this._movieClipSprite.parent;
            this._savedParent.removeSprite(this._movieClipSprite);
         }
      }

      public function set position(point:Point3) : void
      {
         if(this._movieClipSprite.x == point.x &&
            this._movieClipSprite.y == point.z && this._movieClipSprite.z == point.y) return;
         if(isNaN(point.x) || isNaN(point.y) || isNaN(point.z))
            throw new Error("Invalid sprite position");
         // Sprite3D and the renderer share this vertex. Update all axes before
         // invalidating its geometry, without transient extreme coordinates.
         this._movieClipSprite.vertices[0].setValue(point.x,point.z,point.y);
      }

      public function get sprite() : Sprite
      {
         return Sprite(this._movieClipSprite.movieClip);
      }

      public function set sprite(param1:Sprite) : void
      {
         if(this._movieClipSprite.movieClip == param1) return;
         this._movieClipSprite.movieClip = param1;
         this.invalidate();
      }

      public function get sprite3d() : Sprite3D
      {
         return this._movieClipSprite;
      }

      public function destroy() : void
      {
         this._movieClipSprite.movieClip = null;
         this._movieClipSprite = null;
      }

      public function invalidate() : void
      {
         var vertex:Vertex = this._movieClipSprite.vertices[0];
         vertex.setValue(vertex.x,vertex.y,vertex.z);
      }
   }
}
