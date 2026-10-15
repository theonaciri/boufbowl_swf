package away3d.core.session
{
   import away3d.arcane;
   import away3d.containers.*;
   import away3d.core.base.*;
   import away3d.core.render.*;
   import away3d.core.utils.*;
   import away3d.core.vos.*;
   import away3d.events.*;
   import away3d.lights.*;
   import away3d.materials.*;
   import flash.display.*;
   import flash.events.*;
   import flash.geom.*;
   import flash.utils.*;
   import flash.system.Capabilities;
   
   use namespace arcane;
   
   public class AbstractSession extends EventDispatcher
   {
      
      arcane var _containers:Dictionary = new Dictionary(true);
      
      arcane var _shape:Shape;
      
      arcane var _sprite:Sprite;
      
      arcane var _level:int = -1;
      
      arcane var _material:Material;
      
      arcane var _renderSource:Object3D;
      
      arcane var _layerDirty:Boolean;
      
      arcane var _shapeStore:Array;
      
      arcane var _shapeActive:Array;
      
      arcane var _spriteStore:Array;
      
      arcane var _spriteActive:Array;
      
      private var _shapeStores:Dictionary = new Dictionary(true);
      
      private var _shapeActives:Dictionary = new Dictionary(true);
      
      private var _spriteStores:Dictionary = new Dictionary(true);
      
      private var _spriteActives:Dictionary = new Dictionary(true);
      
      private var _spriteLayers:Dictionary = new Dictionary(true);
      
      private var _spriteLayer:Dictionary;
      
      private var _shapeLayers:Dictionary = new Dictionary(true);
      
      private var _shapeLayer:Dictionary;
      
      private var _lightShapeLayers:Dictionary = new Dictionary(true);
      
      private var _lightShapeLayer:Dictionary;
      
      private var _dictionary:Dictionary;
      
      private var _array:Array;
      
      private var _defaultColorTransform:ColorTransform = new ColorTransform();
      
      private var fill:GraphicsBitmapFill = new GraphicsBitmapFill();
      
      private var path:GraphicsTrianglePath = new GraphicsTrianglePath(new Vector.<Number>(3),null,new Vector.<Number>(3));
      
      private var end:GraphicsEndFill = new GraphicsEndFill();
      
      private var drawing:Vector.<IGraphicsData> = Vector.<IGraphicsData>([this.fill,this.path,this.end]);
      
      private var _renderers:Dictionary = new Dictionary(true);
      
      private var _renderer:Renderer;
      
      private var _session:AbstractSession;
      
      private var _sessionupdated:SessionEvent;
      
      private var _sessionDirty:Boolean;
      
      private var _i:uint;
      
      private var _index0:uint;
      
      private var _index1:uint;
      
      private var _index2:uint;
      
      private var v0x:Number;
      
      private var v0y:Number;
      
      private var v1x:Number;
      
      private var v1y:Number;
      
      private var v2x:Number;
      
      private var v2y:Number;
      
      private var a2:Number;
      
      private var b2:Number;
      
      private var c2:Number;
      
      private var d2:Number;
      
      private var m:Matrix = new Matrix();
      
      private var _r:Renderer;
      
      private var _spriteVO:SpriteVO;
      
      private var _mapping:Matrix;
      
      private var _scale:Number;
      
      private var _scaleWidth:Number;
      
      private var _scaleHeight:Number;
      
      private var _vx:Number;
      
      private var _vy:Number;
      
      private var _vertices:Vector.<Number> = new Vector.<Number>();
      
      protected var i:int;
      
      public var layer:DisplayObject;
      
      public var parent:AbstractSession;
      
      public var updated:Boolean;
      
      public var primitives:Array;
      
      public var screenZ:Number;
      
      public var filters:Array;
      
      public var alpha:Number = 1;
      
      public var blendMode:String;
      
      public var sessions:Array = new Array();
      
      public var graphics:Graphics;
      
      public var priconsumers:Dictionary = new Dictionary(true);
      
      public var consumer:Renderer;
      
      public var object3D:Object3D;
      
      public function AbstractSession()
      {
         super();
      }
      
      arcane function updateSession() : void
      {
         if(!this.object3D.scene)
         {
            return;
         }
         this.object3D.scene.arcane::flagSession(this);
         this.notifySessionUpdate();
      }
      
      private function notifySessionUpdate() : void
      {
         if(this._sessionDirty)
         {
            return;
         }
         this._sessionDirty = true;
         if(this is BitmapSession && Boolean(this.object3D))
         {
            this.object3D.scene.arcane::flagSession(this);
         }
         if(!hasEventListener(SessionEvent.SESSION_UPDATED))
         {
            return;
         }
         if(!this._sessionupdated)
         {
            this._sessionupdated = new SessionEvent(SessionEvent.SESSION_UPDATED,this);
         }
         dispatchEvent(this._sessionupdated);
      }
      
      arcane function internalAddSceneSession(param1:AbstractSession) : void
      {
         this.sessions = [param1];
         param1.addOnSessionUpdate(this.onSessionUpdate);
      }
      
      arcane function internalRemoveSceneSession(param1:AbstractSession) : void
      {
         this.sessions = [];
         param1.removeOnSessionUpdate(this.onSessionUpdate);
      }
      
      private function getShapeStore(param1:View3D) : Array
      {
         if(!this._shapeStores[param1])
         {
            return this._shapeStores[param1] = new Array();
         }
         return this._shapeStores[param1];
      }
      
      private function getShapeActive(param1:View3D) : Array
      {
         if(!this._shapeActives[param1])
         {
            return this._shapeActives[param1] = new Array();
         }
         return this._shapeActives[param1];
      }
      
      private function getSpriteStore(param1:View3D) : Array
      {
         if(!this._spriteStores[param1])
         {
            return this._spriteStores[param1] = new Array();
         }
         return this._spriteStores[param1];
      }
      
      private function getSpriteActive(param1:View3D) : Array
      {
         if(!this._spriteActives[param1])
         {
            return this._spriteActives[param1] = new Array();
         }
         return this._spriteActives[param1];
      }
      
      public function getSpriteLayer(param1:View3D) : Dictionary
      {
         if(!this._spriteLayers[param1])
         {
            return this._spriteLayers[param1] = new Dictionary(true);
         }
         return this._spriteLayers[param1];
      }
      
      public function getShapeLayer(param1:View3D) : Dictionary
      {
         if(!this._shapeLayers[param1])
         {
            return this._shapeLayers[param1] = new Dictionary(true);
         }
         return this._shapeLayers[param1];
      }
      
      public function getLightShapeLayer(param1:View3D) : Dictionary
      {
         if(!this._lightShapeLayers[param1])
         {
            return this._lightShapeLayers[param1] = new Dictionary(true);
         }
         return this._lightShapeLayers[param1];
      }
      
      protected function onSessionUpdate(param1:SessionEvent) : void
      {
         this.notifySessionUpdate();
      }
      
      public function get renderer() : Renderer
      {
         return this._renderer;
      }
      
      public function set renderer(param1:Renderer) : void
      {
         var _loc2_:AbstractSession = null;
         if(this._renderer == param1)
         {
            return;
         }
         this._renderer = param1;
         this.clearRenderers();
         for each(_loc2_ in this.sessions)
         {
            _loc2_.clearRenderers();
         }
      }
      
      public function addChildSession(param1:AbstractSession) : void
      {
         if(this.sessions.indexOf(param1) != -1)
         {
            return;
         }
         this.sessions.push(param1);
         param1.addOnSessionUpdate(this.onSessionUpdate);
         param1.parent = this;
      }
      
      public function removeChildSession(param1:AbstractSession) : void
      {
         param1.removeOnSessionUpdate(this.onSessionUpdate);
         var _loc2_:int = this.sessions.indexOf(param1);
         if(_loc2_ == -1)
         {
            return;
         }
         this.sessions.splice(_loc2_,1);
      }
      
      public function clearChildSessions() : void
      {
         for each(this._session in this.sessions)
         {
            this._session.removeOnSessionUpdate(this.onSessionUpdate);
         }
         this.sessions = new Array();
      }
      
      protected function createLayer() : void
      {
         throw new Error("Not implemented");
      }
      
      public function getContainer(param1:View3D) : DisplayObject
      {
         throw new Error("Not implemented");
      }
      
      public function getRenderer(param1:View3D) : Renderer
      {
         if(this._renderers[param1])
         {
            return this._renderers[param1];
         }
         if(this._renderer)
         {
            this._r = this._renderers[param1] = this._renderer.clone();
         }
         else if(this.parent)
         {
            this._r = this._renderers[param1] = this.parent.getRenderer(param1).clone();
         }
         else
         {
            this._r = this._renderers[param1] = param1.session.renderer.clone();
         }
         this._r.arcane::_view = param1;
         this._r.arcane::_session = this;
         return this._r;
      }
      
      public function getTotalFaces(param1:View3D) : int
      {
         var _loc2_:int = int(this.getRenderer(param1).list().length);
         for each(this._session in this.sessions)
         {
            _loc2_ += this._session.getTotalFaces(param1);
         }
         return _loc2_;
      }
      
      public function clear(param1:View3D) : void
      {
         this._sessionDirty = false;
         this.updated = param1.updated || param1.forceUpdate || Boolean(param1.arcane::_updatedSessions[this]);
         for each(this._session in this.sessions)
         {
            this._session.clear(param1);
         }
         if(this.updated)
         {
            this._spriteLayer = this.getSpriteLayer(param1);
            for each(this._array in this._spriteLayer)
            {
               this._array.length = 0;
            }
            this._shapeLayer = this.getShapeLayer(param1);
            for each(this._array in this._shapeLayer)
            {
               this._array.length = 0;
            }
            this._lightShapeLayer = this.getLightShapeLayer(param1);
            for each(this._dictionary in this._lightShapeLayer)
            {
               for each(this._array in this._dictionary)
               {
                  this._array.length = 0;
               }
            }
            this._level = -1;
            this._shapeStore = this.getShapeStore(param1);
            this._shapeActive = this.getShapeActive(param1);
            this.i = this._shapeActive.length;
            while(this.i--)
            {
               this._shape = this._shapeActive.pop();
               this._shape.graphics.clear();
               this._shape.filters = [];
               this._shape.blendMode = BlendMode.NORMAL;
               this._shape.transform.colorTransform = this._defaultColorTransform;
               this._shapeStore.push(this._shape);
            }
            this._spriteStore = this.getSpriteStore(param1);
            this._spriteActive = this.getSpriteActive(param1);
            this.i = this._spriteActive.length;
            while(this.i--)
            {
               this._sprite = this._spriteActive.pop();
               this._sprite.graphics.clear();
               this._sprite.filters = [];
               while(this._sprite.numChildren)
               {
                  this._sprite.removeChildAt(0);
               }
               this._spriteStore.push(this._sprite);
            }
            this.getRenderer(param1).clear();
         }
      }
      
      public function render(param1:View3D) : void
      {
         for each(this._session in this.sessions)
         {
            this._session.render(param1);
         }
         if(this.updated)
         {
            this.getRenderer(param1).render();
         }
         delete param1.arcane::_updatedSessions[this];
      }
      
      public function clearRenderers() : void
      {
         this._renderers = new Dictionary(true);
      }
      
      public function addDisplayObject(param1:DisplayObject) : void
      {
         throw new Error("Not implemented");
      }
      
      public function getSprite(param1:LayerMaterial, param2:int, param3:Sprite = null) : Sprite
      {
         if(!(this._array = this._spriteLayer[param1]))
         {
            this._array = this._spriteLayer[param1] = new Array();
         }
         if(!param3 && param1 != this._material)
         {
            this._level = -1;
            this._material = param1;
         }
         if(this._level >= param2 && Boolean(this._array.length))
         {
            this._sprite = this._array[0];
         }
         else
         {
            this._level = param2;
            this._array.unshift(this._sprite = this.createSprite(param3));
         }
         return this._sprite;
      }
      
      public function getShape(param1:LayerMaterial, param2:int, param3:Sprite) : Shape
      {
         if(!(this._array = this._shapeLayer[param1]))
         {
            this._array = this._shapeLayer[param1] = new Array();
         }
         if(this._level >= param2 && Boolean(this._array.length))
         {
            this._shape = this._array[0];
         }
         else
         {
            this._level = param2;
            this._array.unshift(this._shape = this.createShape(param3));
         }
         return this._shape;
      }
      
      public function getLightShape(param1:LayerMaterial, param2:int, param3:Sprite, param4:AbstractLight) : Shape
      {
         if(!(this._dictionary = this._lightShapeLayer[param1]))
         {
            this._dictionary = this._lightShapeLayer[param1] = new Dictionary(true);
         }
         if(!(this._array = this._dictionary[param4]))
         {
            this._array = this._dictionary[param4] = new Array();
         }
         if(this._level >= param2 && Boolean(this._array.length))
         {
            this._shape = this._array[0];
         }
         else
         {
            this._level = param2;
            this._array.unshift(this._shape = this.createShape(param3));
         }
         return this._shape;
      }
      
      protected function createSprite(param1:Sprite = null) : Sprite
      {
         throw new Error("Not implemented");
      }
      
      protected function createShape(param1:Sprite) : Shape
      {
         if(this._shapeStore.length)
         {
            this._shapeActive.push(this._shape = this._shapeStore.pop());
         }
         else
         {
            this._shapeActive.push(this._shape = new Shape());
         }
         param1.addChild(this._shape);
         this._layerDirty = true;
         return this._shape;
      }
      
      public function renderLine(param1:Number, param2:Number, param3:Number, param4:Number, param5:Number, param6:uint, param7:Number) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         this.graphics.lineStyle(param5,param6,param7);
         this.graphics.moveTo(param1,param2);
         this.graphics.lineTo(param3,param4);
      }
      
      public function renderTriangleBitmapMask(param1:BitmapData, param2:Number, param3:Number, param4:Number, param5:Vector.<Number>, param6:Vector.<int>, param7:uint, param8:uint, param9:Boolean, param10:Boolean, param11:Graphics = null) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         this._index0 = param6[param7] * 2;
         this._index1 = param6[uint(param7 + 1)] * 2;
         this._index2 = param6[uint(param7 + 2)] * 2;
         this.a2 = (this.v1x = param5[this._index1]) - (this.v0x = param5[this._index0]);
         this.b2 = (this.v1y = param5[uint(this._index1 + 1)]) - (this.v0y = param5[uint(this._index0 + 1)]);
         this.c2 = (this.v2x = param5[this._index2]) - this.v0x;
         this.d2 = (this.v2y = param5[uint(this._index2 + 1)]) - this.v0y;
         this.m.identity();
         this.m.scale(param4,param4);
         this.m.translate(param2,param3);
         if(param11)
         {
            param11.lineStyle();
            param11.moveTo(this.v0x,this.v0y);
            param11.beginBitmapFill(param1,this.m,param10,param9 && this.v0x * (this.d2 - this.b2) - this.v1x * this.d2 + this.v2x * this.b2 > 400);
            param11.lineTo(this.v1x,this.v1y);
            param11.lineTo(this.v2x,this.v2y);
            param11.endFill();
         }
         else
         {
            this.graphics.lineStyle();
            this.graphics.moveTo(this.v0x,this.v0y);
            this.graphics.beginBitmapFill(param1,this.m,param10,param9 && this.v0x * (this.d2 - this.b2) - this.v1x * this.d2 + this.v2x * this.b2 > 400);
            this.graphics.lineTo(this.v1x,this.v1y);
            this.graphics.lineTo(this.v2x,this.v2y);
            this.graphics.endFill();
         }
      }
      
      public function renderTriangleBitmap(param1:BitmapData, param2:Vector.<Number>, param3:Vector.<Number>, param4:Vector.<int>, param5:uint, param6:uint, param7:Boolean, param8:Boolean, param9:Graphics = null) : void
      {
         if(!param9 && this._layerDirty)
         {
            this.createLayer();
         }
         this._index0 = param4[param5] * 2;
         this._index1 = param4[uint(param5 + 1)] * 2;
         this._index2 = param4[uint(param5 + 2)] * 2;
         this.fill.bitmapData = param1;
         this.fill.repeat = param8;
         this.fill.smooth = param7;
         this._vertices.length = 0;
         this._vertices[uint(0)] = param3[this._index0];
         this._vertices[uint(1)] = param3[uint(this._index0 + 1)];
         this._vertices[uint(2)] = param3[this._index1];
         this._vertices[uint(3)] = param3[uint(this._index1 + 1)];
         this._vertices[uint(4)] = param3[this._index2];
         this._vertices[uint(5)] = param3[uint(this._index2 + 1)];
         if(Capabilities.playerType == "PlugIn")
         {
            var targetGraphics:Graphics = param9 ? param9 : this.graphics;
            // Ruffle ignores GraphicsTrianglePath.uvtData. Use affine bitmap
            // fills on adaptively subdivided triangles to preserve perspective.
            var vertices:Array = [];
            for(var vertex:int=0;vertex<3;vertex++)
            {
               var depth:Number = param2[vertex*3+2];
               vertices.push([this._vertices[vertex*2],this._vertices[vertex*2+1],
                  param2[vertex*3]*depth,param2[vertex*3+1]*depth,depth]);
            }
            browserTriangle(targetGraphics,param1,vertices[0],vertices[1],vertices[2],param8,param7,0);
            return;
         }
         this.path.vertices = this._vertices;
         this.path.uvtData = param2;
         if(param9)
         {
            param9.lineStyle();
            param9.drawGraphicsData(this.drawing);
         }
         else
         {
            this.graphics.lineStyle();
            this.graphics.drawGraphicsData(this.drawing);
         }
      }
      
      private function browserMidpoint(a:Array,b:Array) : Array
      {
         return [(a[0]+b[0])*0.5,(a[1]+b[1])*0.5,(a[2]+b[2])*0.5,
            (a[3]+b[3])*0.5,(a[4]+b[4])*0.5];
      }

      private function browserTriangle(g:Graphics, bitmap:BitmapData, a:Array,b:Array,c:Array,
         repeat:Boolean,smooth:Boolean,level:int) : void
      {
         var minimum:Number = Math.min(a[4],b[4],c[4]);
         var maximum:Number = Math.max(a[4],b[4],c[4]);
         var extent:Number = Math.max(Math.abs(a[0]-b[0]),Math.abs(a[1]-b[1]),
            Math.abs(a[0]-c[0]),Math.abs(a[1]-c[1]),Math.abs(b[0]-c[0]),Math.abs(b[1]-c[1]));
         if(level < 5 && minimum > 0 && extent*(maximum/minimum-1) > 6)
         {
            var ab:Array=browserMidpoint(a,b);
            var bc:Array=browserMidpoint(b,c);
            var ca:Array=browserMidpoint(c,a);
            browserTriangle(g,bitmap,a,ab,ca,repeat,smooth,level+1);
            browserTriangle(g,bitmap,ab,b,bc,repeat,smooth,level+1);
            browserTriangle(g,bitmap,ca,bc,c,repeat,smooth,level+1);
            browserTriangle(g,bitmap,ab,bc,ca,repeat,smooth,level+1);
            return;
         }
         if(a[4] == 0 || b[4] == 0 || c[4] == 0) return;
         var u0:Number=a[2]/a[4]*bitmap.width;
         var v0:Number=a[3]/a[4]*bitmap.height;
         var du1:Number=b[2]/b[4]*bitmap.width-u0;
         var dv1:Number=b[3]/b[4]*bitmap.height-v0;
         var du2:Number=c[2]/c[4]*bitmap.width-u0;
         var dv2:Number=c[3]/c[4]*bitmap.height-v0;
         var determinant:Number=du1*dv2-du2*dv1;
         if(Math.abs(determinant) < 0.00000001) return;
         var dx1:Number=b[0]-a[0];
         var dy1:Number=b[1]-a[1];
         var dx2:Number=c[0]-a[0];
         var dy2:Number=c[1]-a[1];
         var mapping:Matrix=new Matrix((dx1*dv2-dx2*dv1)/determinant,
            (dy1*dv2-dy2*dv1)/determinant,(dx2*du1-dx1*du2)/determinant,
            (dy2*du1-dy1*du2)/determinant);
         mapping.tx=a[0]-mapping.a*u0-mapping.c*v0;
         mapping.ty=a[1]-mapping.b*u0-mapping.d*v0;
         g.lineStyle();
         g.beginBitmapFill(bitmap,mapping,repeat,smooth);
         g.moveTo(a[0],a[1]);
         g.lineTo(b[0],b[1]);
         g.lineTo(c[0],c[1]);
         g.lineTo(a[0],a[1]);
         g.endFill();
      }

      public function renderDot(param1:int, param2:Number, param3:Number, param4:Number, param5:Graphics = null, param6:int = 1) : void
      {
         var _loc8_:Number = NaN;
         if(!param5 && this._layerDirty)
         {
            this.createLayer();
         }
         var _loc7_:Graphics = param5 ? param5 : this.graphics;
         _loc7_.lineStyle();
         _loc7_.beginFill(param1,param2);
         if(param6 == 1)
         {
            _loc7_.drawRect(param3,param4,param6,param6);
         }
         else
         {
            _loc8_ = param6 * 0.5;
            _loc7_.drawRect(param3 - _loc8_,param4 - _loc8_,param6,param6);
         }
         _loc7_.endFill();
      }
      
      public function renderTriangleColor(param1:int, param2:Number, param3:Vector.<Number>, param4:Vector.<String>, param5:Vector.<int>, param6:Number, param7:Number, param8:Graphics = null) : void
      {
         if(!param8 && this._layerDirty)
         {
            this.createLayer();
         }
         var _loc9_:Graphics = param8 ? param8 : this.graphics;
         if(param7 - param6 > 3)
         {
            _loc9_.lineStyle();
            this._i = param6;
            while(this._i < param7)
            {
               this._index0 = param5[uint(this._i++)] * 2;
               switch(param4[uint(this._i - param6 - 1)])
               {
                  case "M":
                     _loc9_.moveTo(param3[this._index0],param3[uint(this._index0 + 1)]);
                     if(this._i - 1 == param6)
                     {
                        _loc9_.beginFill(param1,param2);
                     }
                     break;
                  case "L":
                     _loc9_.lineTo(param3[this._index0],param3[uint(this._index0 + 1)]);
                     break;
                  case "C":
                     this._index1 = param5[uint(this._i++)] * 2;
                     _loc9_.curveTo(param3[this._index0],param3[uint(this._index0 + 1)],param3[this._index1],param3[uint(this._index1 + 1)]);
               }
            }
            _loc9_.endFill();
         }
         else
         {
            this._index0 = param5[param6] * 2;
            this._index1 = param5[param6 + 1] * 2;
            this._index2 = param5[param6 + 2] * 2;
            _loc9_.lineStyle();
            _loc9_.moveTo(param3[this._index0],param3[this._index0 + 1]);
            _loc9_.beginFill(param1,param2);
            _loc9_.lineTo(param3[this._index1],param3[this._index1 + 1]);
            _loc9_.lineTo(param3[this._index2],param3[this._index2 + 1]);
            _loc9_.endFill();
         }
      }
      
      public function renderTriangleLine(param1:Number, param2:int, param3:Number, param4:Vector.<Number>, param5:Vector.<String>, param6:Vector.<int>, param7:Number, param8:Number) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         this.graphics.lineStyle(param1,param2,param3);
         this.i = param7;
         if(param8 - param7 > 3)
         {
            while(this.i < param8)
            {
               this._index0 = param6[uint(this.i++)] * 2;
               switch(param5[uint(this.i - param7 - 1)])
               {
                  case "M":
                     this.graphics.moveTo(param4[this._index0],param4[uint(this._index0 + 1)]);
                     break;
                  case "L":
                     this.graphics.lineTo(param4[this._index0],param4[uint(this._index0 + 1)]);
                     break;
                  case "C":
                     this._index1 = param6[uint(this.i++)] * 2;
                     this.graphics.curveTo(param4[this._index0],param4[uint(this._index0 + 1)],param4[this._index1],param4[uint(this._index1 + 1)]);
               }
            }
         }
         else if(param8 - param7 > 2)
         {
            this._index0 = param6[param7] * 2;
            this._index1 = param6[uint(param7 + 1)] * 2;
            this._index2 = param6[uint(param7 + 2)] * 2;
            this.graphics.moveTo(this.v0x = param4[this._index0],this.v0y = param4[uint(this._index0 + 1)]);
            this.graphics.lineTo(param4[this._index1],param4[uint(this._index1 + 1)]);
            this.graphics.lineTo(param4[this._index2],param4[uint(this._index2 + 1)]);
            this.graphics.lineTo(this.v0x,this.v0y);
         }
         else
         {
            this._index0 = param6[param7] * 2;
            this._index1 = param6[uint(param7 + 1)] * 2;
            this.graphics.moveTo(this.v0x = param4[this._index0],this.v0y = param4[uint(this._index0 + 1)]);
            this.graphics.lineTo(param4[this._index1],param4[uint(this._index1 + 1)]);
            this.graphics.lineTo(this.v0x,this.v0y);
         }
      }
      
      public function renderTriangleLineFill(param1:Number, param2:int, param3:Number, param4:int, param5:Number, param6:Vector.<Number>, param7:Vector.<String>, param8:Vector.<int>, param9:int, param10:int) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         if(param5 > 0)
         {
            this.graphics.lineStyle(param1,param4,param5);
         }
         else
         {
            this.graphics.lineStyle();
         }
         if(param10 - param9 > 3)
         {
            this._i = param9;
            while(this._i < param10)
            {
               this._index0 = param8[uint(this._i++)] * 2;
               switch(param7[uint(this._i - param9 - 1)])
               {
                  case "M":
                     this.graphics.moveTo(param6[this._index0],param6[uint(this._index0 + 1)]);
                     if(this._i - 1 == param9 && param3 > 0)
                     {
                        this.graphics.beginFill(param2,param3);
                     }
                     break;
                  case "L":
                     this.graphics.lineTo(param6[this._index0],param6[uint(this._index0 + 1)]);
                     break;
                  case "C":
                     this._index1 = param8[uint(this._i++)] * 2;
                     this.graphics.curveTo(param6[this._index0],param6[uint(this._index0 + 1)],param6[this._index1],param6[uint(this._index1 + 1)]);
               }
            }
         }
         else
         {
            this._index0 = param8[param9] * 2;
            this._index1 = param8[uint(param9 + 1)] * 2;
            this._index2 = param8[uint(param9 + 2)] * 2;
            this.graphics.moveTo(this.v0x = param6[this._index0],this.v0y = param6[uint(this._index0 + 1)]);
            if(param3 > 0)
            {
               this.graphics.beginFill(param2,param3);
            }
            this.graphics.lineTo(param6[this._index1],param6[uint(this._index1 + 1)]);
            this.graphics.lineTo(param6[this._index2],param6[uint(this._index2 + 1)]);
            if(param5 > 0)
            {
               this.graphics.lineTo(this.v0x,this.v0y);
            }
         }
         if(param3 > 0)
         {
            this.graphics.endFill();
         }
      }
      
      public function renderSpriteLine(param1:Number, param2:int, param3:Number, param4:uint, param5:ViewSourceObject, param6:Renderer) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         this.graphics.lineStyle(param1,param2,param3);
         this._spriteVO = param6.primitiveElements[param4] as SpriteVO;
         this._scale = param6.primitiveProperties[uint(param4 * 9 + 8)];
         this._scaleWidth = this._scale * this._spriteVO.width;
         this._scaleHeight = this._scale * this._spriteVO.height;
         this._index0 = param5.screenIndices[uint(param6.primitiveProperties[uint(param4 * 9)])] * 2;
         this._vx = param5.screenVertices[this._index0];
         this._vy = param5.screenVertices[uint(this._index0 + 1)];
         if(this._spriteVO.rotation != 0)
         {
            this.graphics.moveTo(this._vx + this._spriteVO.topleftx * this._scaleWidth,this._vy + this._spriteVO.toplefty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.toprightx * this._scaleWidth,this._vy + this._spriteVO.toprighty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.bottomrightx * this._scaleWidth,this._vy + this._spriteVO.bottomrighty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.bottomleftx * this._scaleWidth,this._vy + this._spriteVO.bottomlefty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.topleftx * this._scaleWidth,this._vy + this._spriteVO.toplefty * this._scaleHeight);
         }
         else
         {
            this.graphics.drawRect(this._vx + this._spriteVO.minX * this._scaleWidth,this._vy + this._spriteVO.minY * this._scaleHeight,(this._spriteVO.maxX - this._spriteVO.minX) * this._scaleWidth,(this._spriteVO.maxY - this._spriteVO.minY) * this._scaleHeight);
         }
      }
      
      public function renderSpriteColor(param1:int, param2:Number, param3:uint, param4:ViewSourceObject, param5:Renderer) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         this.graphics.lineStyle();
         this._spriteVO = param5.primitiveElements[param3] as SpriteVO;
         this._scale = param5.primitiveProperties[uint(param3 * 9 + 8)];
         this._scaleWidth = this._scale * this._spriteVO.width;
         this._scaleHeight = this._scale * this._spriteVO.height;
         this._index0 = param4.screenIndices[uint(param5.primitiveProperties[uint(param3 * 9)])] * 2;
         this._vx = param4.screenVertices[this._index0];
         this._vy = param4.screenVertices[uint(this._index0 + 1)];
         if(this._spriteVO.rotation != 0)
         {
            this.graphics.beginFill(param1,param2);
            this.graphics.moveTo(this._vx + this._spriteVO.topleftx * this._scaleWidth,this._vy + this._spriteVO.toplefty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.toprightx * this._scaleWidth,this._vy + this._spriteVO.toprighty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.bottomrightx * this._scaleWidth,this._vy + this._spriteVO.bottomrighty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.bottomleftx * this._scaleWidth,this._vy + this._spriteVO.bottomlefty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.topleftx * this._scaleWidth,this._vy + this._spriteVO.toplefty * this._scaleHeight);
            this.graphics.endFill();
         }
         else
         {
            this.graphics.beginFill(param1,param2);
            this.graphics.drawRect(this._vx + this._spriteVO.minX * this._scaleWidth,this._vy + this._spriteVO.minY * this._scaleHeight,(this._spriteVO.maxX - this._spriteVO.minX) * this._scaleWidth,(this._spriteVO.maxY - this._spriteVO.minY) * this._scaleHeight);
            this.graphics.endFill();
         }
      }
      
      public function renderSpriteBitmap(param1:BitmapData, param2:Boolean, param3:uint, param4:ViewSourceObject, param5:Renderer) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         this.graphics.lineStyle();
         this._spriteVO = param5.primitiveElements[param3] as SpriteVO;
         this._scale = param5.primitiveProperties[uint(param3 * 9 + 8)];
         this._scaleWidth = this._scale * param1.width;
         this._scaleHeight = this._scale * param1.height;
         this._index0 = param4.screenIndices[uint(param5.primitiveProperties[uint(param3 * 9)])] * 2;
         this._vx = param4.screenVertices[this._index0];
         this._vy = param4.screenVertices[uint(this._index0 + 1)];
         this._mapping = this._spriteVO.mapping.clone();
         this._mapping.scale(this._scale,this._scale);
         this._mapping.translate(this._vx - this._scale * param1.width / 2,this._vy - this._scale * param1.height / 2);
         if(this._spriteVO.rotation != 0)
         {
            this.graphics.beginBitmapFill(param1,this._mapping,false,param2);
            this.graphics.moveTo(this._vx + this._spriteVO.topleftx * this._scaleWidth,this._vy + this._spriteVO.toplefty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.toprightx * this._scaleWidth,this._vy + this._spriteVO.toprighty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.bottomrightx * this._scaleWidth,this._vy + this._spriteVO.bottomrighty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.bottomleftx * this._scaleWidth,this._vy + this._spriteVO.bottomlefty * this._scaleHeight);
            this.graphics.lineTo(this._vx + this._spriteVO.topleftx * this._scaleWidth,this._vy + this._spriteVO.toplefty * this._scaleHeight);
            this.graphics.endFill();
         }
         else
         {
            this.graphics.beginBitmapFill(param1,this._mapping,false,param2);
            this.graphics.drawRect(this._vx + this._spriteVO.minX * this._scaleWidth,this._vy + this._spriteVO.minY * this._scaleHeight,(this._spriteVO.maxX - this._spriteVO.minX) * this._scaleWidth,(this._spriteVO.maxY - this._spriteVO.minY) * this._scaleHeight);
            this.graphics.endFill();
         }
      }
      
      public function renderFogColor(param1:int, param2:Number, param3:Number, param4:Number, param5:Number, param6:Number) : void
      {
         if(this._layerDirty)
         {
            this.createLayer();
         }
         this.graphics.lineStyle();
         this.graphics.beginFill(param1,param2);
         this.graphics.drawRect(param3,param5,param4 - param3,param6 - param5);
         this.graphics.endFill();
      }
      
      public function clone() : AbstractSession
      {
         throw new Error("Not implemented");
      }
      
      public function addOnSessionUpdate(param1:Function) : void
      {
         addEventListener(SessionEvent.SESSION_UPDATED,param1,false,0,false);
      }
      
      public function removeOnSessionUpdate(param1:Function) : void
      {
         removeEventListener(SessionEvent.SESSION_UPDATED,param1,false);
      }
   }
}

