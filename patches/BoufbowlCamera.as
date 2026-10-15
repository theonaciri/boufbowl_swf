package com.ankamagames.boufbowl.resolution.display.camera
{
   import away3d.cameras.Camera3D;
   import com.ankamagames.xgaming.utils.errors.IllegalArgumentError;
   import com.ankamagames.xgaming.utils.event.PropertyChangedEvent;
   import com.ankamagames.xgaming.utils.math.angle.degreesToRadians;
   import com.ankamagames.xgaming.utils.math.angle.rangedDegrees;
   import flash.events.EventDispatcher;
   import flash.geom.Vector3D;
   import flash.geom.Matrix3D;
   import flash.system.Capabilities;

   public class BoufbowlCamera extends EventDispatcher
   {

      private var _radius:Number = 0;

      private var _zoom:Number = 10;

      private var _azimuth:Number = 0;

      private var _lateralPan:Number = 0;

      private var _frontalPan:Number = 0;

      private var _elevation:Number = 0;

      private var _centerPoint:Vector3D;

      private var _projectionType:ProjectionType;

      private var _camera:Camera3D;

      public function BoufbowlCamera()
      {
         super();
         this.init();
      }

      public function get camera() : Camera3D
      {
         return this._camera;
      }

      public function get centerPoint() : Vector3D
      {
         return this._centerPoint;
      }

      public function set centerPoint(param1:Vector3D) : void
      {
         this.assertVector3DValid(param1);
         if(this._centerPoint.equals(param1))
         {
            return;
         }
         this._centerPoint = param1;
         this.updateCamera();
      }

      public function get radius() : Number
      {
         return this._radius;
      }

      public function set radius(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw IllegalArgumentError("radius can\'t be NaN");
         }
         if(this._radius == param1)
         {
            return;
         }
         this._radius = param1;
         this.updateCamera();
      }

      public function get zoom() : Number
      {
         return this._zoom;
      }

      public function set zoom(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw IllegalArgumentError("zoom can\'t be NaN");
         }
         if(this._zoom == param1)
         {
            return;
         }
         this._zoom = param1;
         this._camera.zoom = this._zoom;
      }

      public function get azimuth() : Number
      {
         return this._azimuth;
      }

      public function set azimuth(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw IllegalArgumentError("azimuth can\'t be NaN");
         }
         var _loc2_:Number = rangedDegrees(param1);
         if(this._azimuth == _loc2_)
         {
            return;
         }
         this._azimuth = _loc2_;
         this.updateCamera();
      }

      public function get lateralPan() : Number
      {
         return this._lateralPan;
      }

      public function set lateralPan(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw IllegalArgumentError("lateralPan can\'t be NaN");
         }
         if(this._lateralPan == param1)
         {
            return;
         }
         this._lateralPan = param1;
         this.updateCamera();
      }

      public function get frontalPan() : Number
      {
         return this._frontalPan;
      }

      public function set frontalPan(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw IllegalArgumentError("frontalPan can\'t be NaN");
         }
         if(this._frontalPan == param1)
         {
            return;
         }
         this._frontalPan = param1;
         this.updateCamera();
      }

      public function get elevation() : Number
      {
         return this._elevation;
      }

      public function set elevation(param1:Number) : void
      {
         if(isNaN(param1))
         {
            throw IllegalArgumentError("elevation can\'t be NaN");
         }
         if(this._elevation == param1)
         {
            return;
         }
         this._elevation = param1;
         this.updateCamera();
      }

      private function init() : void
      {
         this._centerPoint = new Vector3D();
         this._camera = new Camera3D();
         this._camera.lens = ProjectionTypes.PERSPECTIVE.createLens();
         this._zoom = this._camera.zoom;
         this.updateCamera();
      }

      private function updateCamera() : void
      {
         var _loc1_:Number = degreesToRadians(this._elevation);
         var _loc2_:Number = Math.cos(_loc1_);
         var _loc3_:Number = Math.sin(_loc1_);
         var _loc4_:Number = degreesToRadians(this._azimuth);
         var _loc5_:Number = Math.cos(_loc4_);
         var _loc6_:Number = Math.sin(_loc4_);
         var _loc7_:Vector3D = new Vector3D(this._lateralPan * -_loc6_ + this._frontalPan * -_loc5_,0,this._lateralPan * _loc5_ + this._frontalPan * -_loc6_);
         var _loc8_:Vector3D = this._centerPoint.add(_loc7_);
         var _loc9_:Vector3D = new Vector3D(this._radius * _loc2_ * _loc5_,this._radius * _loc3_,this._radius * _loc2_ * _loc6_);
         var _loc10_:Vector3D = _loc8_.add(_loc9_);
         this._camera.moveTo(_loc10_.x,_loc10_.y,_loc10_.z);
         if(Capabilities.playerType == "PlugIn")
         {
            // Matrix3D.pointAt is a stub in Ruffle. Build the camera's local
            // right/up/forward basis directly. pointAt's up argument is an
            // object-relative axis; match Flash's cross-product order here.
            var forward:Vector3D = _loc8_.subtract(_loc10_);
            if(forward.lengthSquared > 0.000000000001)
            {
               forward.normalize();
               var right:Vector3D = forward.crossProduct(new Vector3D(0,-1,0));
               if(right.lengthSquared < 0.000000000001)
                  right = new Vector3D(1,0,0);
               else
                  right.normalize();
               var up:Vector3D = forward.crossProduct(right);
               up.normalize();
               this._camera.transform = new Matrix3D(new <Number>[
                  right.x,right.y,right.z,0,
                  up.x,up.y,up.z,0,
                  forward.x,forward.y,forward.z,0,
                  _loc10_.x,_loc10_.y,_loc10_.z,1
               ]);
            }
         }
         else
         {
            this._camera.lookAt(_loc8_);
         }
         dispatchEvent(new PropertyChangedEvent(CameraProperties.PLACEMENT));
      }

      private function assertVector3DValid(param1:Vector3D) : void
      {
         if(isNaN(param1.x))
         {
            throw new ArgumentError("the Vector3D x property can\'t be NaN");
         }
         if(isNaN(param1.y))
         {
            throw new ArgumentError("the Vector3D y property can\'t be NaN");
         }
         if(isNaN(param1.z))
         {
            throw new ArgumentError("the Vector3D z property can\'t be NaN");
         }
      }
   }
}

