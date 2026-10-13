package away3d.loaders
{
   import away3d.animators.*;
   import away3d.animators.data.*;
   import away3d.arcane;
   import away3d.containers.*;
   import away3d.core.base.*;
   import away3d.core.utils.*;
   import away3d.loaders.data.*;
   import away3d.loaders.utils.*;
   import flash.geom.*;
   import flash.utils.*;
   
   use namespace arcane;
   
   public class Collada extends AbstractParser
   {
      
      private var collada:XML;
      
      private var animationLibrary:AnimationLibrary;
      
      private var channelLibrary:ChannelLibrary;
      
      private var yUp:Boolean;
      
      private var toRADIANS:Number = 0.017453292519943295;
      
      private var rotationMatrix:Matrix3D = new Matrix3D();
      
      private var scalingMatrix:Matrix3D = new Matrix3D();
      
      private var translationMatrix:Matrix3D = new Matrix3D();
      
      private var VALUE_X:String;
      
      private var VALUE_Y:String;
      
      private var VALUE_Z:String;
      
      private var VALUE_U:String = "S";
      
      private var VALUE_V:String = "T";
      
      private var _geometryArray:Array;
      
      private var _geometryArrayLength:int;
      
      private var _channelArray:Array;
      
      private var _channelArrayLength:int;
      
      private var _defaultAnimationClip:AnimationData;
      
      private var _haveClips:Boolean = false;
      
      private var _skinControllers:Array = [];
      
      private var _skinController:SkinController;
      
      public var scaling:Number;
      
      public var shading:Boolean;
      
      public function Collada(param1:Object = null)
      {
         super(param1);
         this.scaling = ini.getNumber("scaling",1);
         this.shading = ini.getBoolean("shading",false);
         centerMeshes = ini.getBoolean("centerMeshes",false);
         arcane::_container = new ObjectContainer3D(ini);
         arcane::_container.name = "collada";
         arcane::_container.materialLibrary = _materialLibrary;
         arcane::_container.geometryLibrary = _geometryLibrary;
         this.animationLibrary = arcane::_container.animationLibrary = new AnimationLibrary();
         this.channelLibrary = new ChannelLibrary();
         arcane::binary = false;
      }
      
      public static function parse(param1:*, param2:Object = null) : ObjectContainer3D
      {
         return Loader3D.parse(param1,Collada,param2).handle as ObjectContainer3D;
      }
      
      public static function load(param1:String, param2:Object = null) : Loader3D
      {
         return Loader3D.load(param1,Collada,param2);
      }
      
      private function buildAnimations() : void
      {
         var _loc1_:Bone = null;
         var _loc2_:AnimationData = null;
         var _loc3_:BonesAnimator = null;
         var _loc4_:Array = null;
         var _loc5_:String = null;
         var _loc6_:String = null;
         var _loc7_:String = null;
         var _loc8_:String = null;
         var _loc9_:String = null;
         var _loc10_:String = null;
         var _loc11_:ChannelData = null;
         var _loc12_:Channel = null;
         var _loc13_:Vector.<Number> = null;
         for each(this._skinController in this._skinControllers)
         {
            _loc1_ = (_container as ObjectContainer3D).getBoneByName(this._skinController.name);
            if(_loc1_)
            {
               this._skinController.joint = _loc1_.joint;
               _loc1_.controller = this._skinController;
            }
            else
            {
               Debug.warning("no joint found for " + this._skinController.name);
            }
         }
         for each(_loc2_ in this.animationLibrary)
         {
            switch(_loc2_.animationType)
            {
               case AnimationDataType.SKIN_ANIMATION:
                  _loc3_ = new BonesAnimator();
                  _loc3_.target = _container;
                  for each(_loc11_ in _loc2_.channels)
                  {
                     _loc12_ = _loc11_.channel;
                     _loc3_.addChannel(_loc12_);
                     _loc13_ = _loc12_.times;
                     if(_loc2_.start > _loc13_[0])
                     {
                        _loc2_.start = _loc13_[0];
                     }
                     if(_loc2_.end < _loc13_[_loc13_.length - 1])
                     {
                        _loc2_.end = _loc13_[_loc13_.length - 1];
                     }
                     if(_loc12_.target is Bone)
                     {
                        _loc5_ = "jointRotationX";
                        _loc6_ = "jointRotationY";
                        _loc7_ = "jointRotationZ";
                        _loc8_ = "jointScaleX";
                        _loc9_ = "jointScaleY";
                        _loc10_ = "jointScaleZ";
                     }
                     else
                     {
                        _loc5_ = "rotationX";
                        _loc6_ = "rotationY";
                        _loc7_ = "rotationZ";
                        _loc8_ = "scaleX";
                        _loc9_ = "scaleY";
                        _loc10_ = "scaleZ";
                     }
                     switch(_loc11_.type)
                     {
                        case "translateX":
                        case "translationX":
                        case "transform(3)(0)":
                           _loc12_.type = Vector.<String>(["x"]);
                           if(this.yUp)
                           {
                              for each(_loc4_ in _loc12_.param)
                              {
                                 _loc4_[0] *= -1 * this.scaling;
                              }
                           }
                           break;
                        case "translateY":
                        case "translationY":
                        case "transform(3)(1)":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>(["y"]);
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>(["z"]);
                           }
                           for each(_loc4_ in _loc12_.param)
                           {
                              _loc4_[0] *= this.scaling;
                           }
                           break;
                        case "translateZ":
                        case "translationZ":
                        case "transform(3)(2)":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>(["z"]);
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>(["y"]);
                           }
                           for each(_loc4_ in _loc12_.param)
                           {
                              _loc4_[0] *= this.scaling;
                           }
                           break;
                        case "jointOrientX":
                           _loc12_.type = Vector.<String>(["rotationX"]);
                           if(this.yUp)
                           {
                              for each(_loc4_ in _loc12_.param)
                              {
                                 _loc4_[0] *= -1;
                              }
                           }
                           break;
                        case "rotateXANGLE":
                        case "rotateX":
                        case "RotX":
                           _loc12_.type = Vector.<String>([_loc5_]);
                           if(this.yUp)
                           {
                              for each(_loc4_ in _loc12_.param)
                              {
                                 _loc4_[0] *= -1;
                              }
                           }
                           break;
                        case "jointOrientY":
                           _loc12_.type = Vector.<String>(["rotationY"]);
                           for each(_loc4_ in _loc12_.param)
                           {
                              _loc4_[0] *= -1;
                           }
                           break;
                        case "rotateYANGLE":
                        case "rotateY":
                        case "RotY":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>([_loc6_]);
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>([_loc7_]);
                           }
                           for each(_loc4_ in _loc12_.param)
                           {
                              _loc4_[0] *= -1;
                           }
                           break;
                        case "jointOrientZ":
                           _loc12_.type = Vector.<String>(["rotationZ"]);
                           for each(_loc4_ in _loc12_.param)
                           {
                              _loc4_[0] *= -1;
                           }
                           break;
                        case "rotateZANGLE":
                        case "rotateZ":
                        case "RotZ":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>([_loc7_]);
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>([_loc6_]);
                           }
                           for each(_loc4_ in _loc12_.param)
                           {
                              _loc4_[0] *= -1;
                           }
                           break;
                        case "scaleX":
                        case "transform(0)(0)":
                           _loc12_.type = Vector.<String>([_loc8_]);
                           break;
                        case "scaleY":
                        case "transform(1)(1)":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>([_loc9_]);
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>([_loc10_]);
                           }
                           break;
                        case "scaleZ":
                        case "transform(2)(2)":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>([_loc10_]);
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>([_loc9_]);
                           }
                           break;
                        case "translate":
                        case "translation":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>(["x","y","z"]);
                              for each(_loc4_ in _loc12_.param)
                              {
                                 _loc4_[0] *= -1;
                              }
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>(["x","z","y"]);
                           }
                           for each(_loc4_ in _loc12_.param)
                           {
                              _loc4_[0] *= this.scaling;
                              _loc4_[1] *= this.scaling;
                              _loc4_[2] *= this.scaling;
                           }
                           break;
                        case "scale":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>([_loc8_,_loc9_,_loc10_]);
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>([_loc8_,_loc10_,_loc9_]);
                           }
                           break;
                        case "rotate":
                           if(this.yUp)
                           {
                              _loc12_.type = Vector.<String>([_loc5_,_loc6_,_loc7_]);
                              for each(_loc4_ in _loc12_.param)
                              {
                                 _loc4_[0] *= -1;
                                 _loc4_[1] *= -1;
                                 _loc4_[2] *= -1;
                              }
                           }
                           else
                           {
                              _loc12_.type = Vector.<String>([_loc5_,_loc7_,_loc6_]);
                              for each(_loc4_ in _loc12_.param)
                              {
                                 _loc4_[1] *= -1;
                                 _loc4_[2] *= -1;
                              }
                           }
                           break;
                        case "matrix":
                        case "transform":
                           _loc12_.type = Vector.<String>(["transform"]);
                           break;
                        case "visibility":
                           _loc12_.type = Vector.<String>(["visibility"]);
                     }
                  }
                  _loc3_.delay = _loc2_.start;
                  _loc3_.arcane::_totalFrames = (_loc2_.end - _loc2_.start) * _loc3_.fps;
                  _loc2_.animator = _loc3_;
                  break;
               case AnimationDataType.VERTEX_ANIMATION:
            }
         }
      }
      
      private function getIntArray(param1:String) : Array
      {
         param1 = param1.split("\r\n").join(" ");
         param1 = param1.split("\n").join(" ");
         var _loc2_:Array = param1.split(" ");
         var _loc3_:Array = [];
         var _loc4_:Number = _loc2_.length;
         var _loc5_:Number = 0;
         while(_loc5_ < _loc4_)
         {
            if(_loc2_[_loc5_] != "")
            {
               _loc3_.push(int(_loc2_[_loc5_]));
            }
            _loc5_++;
         }
         return _loc3_;
      }
      
      private function getNumberArray(param1:String) : Array
      {
         param1 = param1.split("\r\n").join(" ");
         param1 = param1.split("\n").join(" ");
         var _loc2_:Array = param1.split(" ");
         var _loc3_:Array = [];
         var _loc4_:Number = _loc2_.length;
         var _loc5_:Number = 0;
         while(_loc5_ < _loc4_)
         {
            if(_loc2_[_loc5_] != "")
            {
               _loc3_.push(Number(_loc2_[_loc5_]));
            }
            _loc5_++;
         }
         return _loc3_;
      }
      
      private function getStringArray(param1:String) : Array
      {
         param1 = param1.split("\r\n").join(" ");
         param1 = param1.split("\n").join(" ");
         return param1.split(" ");
      }
      
      private function rotateMatrix(param1:Array) : Matrix3D
      {
         this.rotationMatrix.identity();
         if(this.yUp)
         {
            this.rotationMatrix.appendRotation(param1[3],new Vector3D(param1[0],-param1[1],-param1[2]));
         }
         else
         {
            this.rotationMatrix.appendRotation(-param1[3],new Vector3D(param1[0],param1[2],param1[1]));
         }
         return this.rotationMatrix;
      }
      
      private function translateMatrix(param1:Array) : Matrix3D
      {
         this.translationMatrix.identity();
         if(this.yUp)
         {
            this.translationMatrix.appendTranslation(-param1[0] * this.scaling,param1[1] * this.scaling,param1[2] * this.scaling);
         }
         else
         {
            this.translationMatrix.appendTranslation(param1[0] * this.scaling,param1[2] * this.scaling,param1[1] * this.scaling);
         }
         return this.translationMatrix;
      }
      
      private function scaleMatrix(param1:Array) : Matrix3D
      {
         this.scalingMatrix.identity();
         if(this.yUp)
         {
            this.scalingMatrix.appendScale(param1[0],param1[1],param1[2]);
         }
         else
         {
            this.scalingMatrix.appendScale(param1[0],param1[2],param1[1]);
         }
         return this.scalingMatrix;
      }
      
      private function getId(param1:String) : String
      {
         return param1.split("#")[1];
      }
      
      override protected function getFileType() : String
      {
         return "Collada";
      }
      
      override arcane function prepareData(param1:*) : void
      {
         this.collada = Cast.xml(param1);
         default xml namespace = this.collada.namespace();
         Debug.trace(" ! ------------- Begin Parse Collada -------------");
         this.yUp = this.collada["asset"].up_axis == "Y_UP" || String(this.collada["asset"].up_axis) == "";
         if(this.yUp)
         {
            this.VALUE_X = "X";
            this.VALUE_Y = "Y";
            this.VALUE_Z = "Z";
         }
         else
         {
            this.VALUE_X = "X";
            this.VALUE_Y = "Z";
            this.VALUE_Z = "Y";
         }
         this.parseScene();
         this.parseAnimationClips();
      }
      
      override arcane function parseNext() : void
      {
         default xml namespace = this.collada.namespace();
         if(_parsedChunks < this._geometryArrayLength)
         {
            this.parseGeometryData(this._geometryArray[_parsedChunks]);
         }
         else
         {
            this.parseChannelData(this._channelArray[-this._geometryArrayLength + _parsedChunks]);
         }
         ++_parsedChunks;
         if(_parsedChunks == _totalChunks)
         {
            buildMaterials();
            buildContainers(_containerData,_container as ObjectContainer3D);
            this.buildAnimations();
            notifySuccess();
         }
         else
         {
            notifyProgress();
         }
      }
      
      private function parseScene() : void
      {
         var scene:XML = null;
         var node:XML = null;
         default xml namespace = this.collada.namespace();
         scene = this.collada["library_visual_scenes"].visual_scene.(@id == getId(collada["scene"].instance_visual_scene.@url))[0];
         if(scene == null)
         {
            Debug.trace(" ! ------------- No scene to parse -------------");
            return;
         }
         Debug.trace(" ! ------------- Begin Parse Scene -------------");
         _containerData = new ContainerData();
         for each(node in scene["node"])
         {
            this.parseNode(node,_containerData);
         }
         Debug.trace(" ! ------------- End Parse Scene -------------");
         this._geometryArray = geometryLibrary.getGeometryArray();
         this._geometryArrayLength = this._geometryArray.length;
         _totalChunks += this._geometryArrayLength;
      }
      
      private function parseNode(param1:XML, param2:ContainerData) : void
      {
         var boneData:BoneData;
         var _transform:Matrix3D = null;
         var _objectData:ObjectData = null;
         var nodeName:String = null;
         var geo:XML = null;
         var ctrlr:XML = null;
         var sid:String = null;
         var instance_material:XML = null;
         var arrayChild:Array = null;
         var childNode:XML = null;
         var m:Matrix3D = null;
         var node:XML = param1;
         var parent:ContainerData = param2;
         default xml namespace = this.collada.namespace();
         if(String(node["instance_light"].@url) != "" || String(node["instance_camera"].@url) != "")
         {
            return;
         }
         if(String(node["instance_controller"]) == "" && String(node["instance_geometry"]) == "")
         {
            if(String(node.@type) == "JOINT")
            {
               _objectData = new BoneData();
            }
            else
            {
               if(String(node["instance_node"].@url) == "" && (String(node["node"]) == "" || parent is BoneData))
               {
                  return;
               }
               _objectData = new ContainerData();
            }
         }
         else
         {
            _objectData = new MeshData();
         }
         parent.children.push(_objectData);
         if(String(node.@type) == "JOINT")
         {
            _objectData.id = node.@sid;
         }
         else
         {
            _objectData.id = node.@id;
         }
         _objectData.name = node.@id;
         _transform = _objectData.transform;
         Debug.trace(" + Parse Node : " + _objectData.id + " : " + _objectData.name);
         boneData = _objectData as BoneData;
         for each(childNode in node.children())
         {
            arrayChild = this.getNumberArray(childNode);
            nodeName = String(childNode.name()["localName"]);
            switch(nodeName)
            {
               case "translate":
                  _transform.prepend(this.translateMatrix(arrayChild));
                  break;
               case "rotate":
                  sid = childNode.@sid;
                  if(_objectData is BoneData && (sid == "rotateX" || sid == "rotateY" || sid == "rotateZ" || sid == "rotX" || sid == "rotY" || sid == "rotZ"))
                  {
                     boneData.jointTransform.prepend(this.rotateMatrix(arrayChild));
                  }
                  else
                  {
                     _transform.prepend(this.rotateMatrix(arrayChild));
                  }
                  break;
               case "scale":
                  if(_objectData is BoneData)
                  {
                     boneData.jointTransform.prepend(this.scaleMatrix(arrayChild));
                  }
                  else
                  {
                     _transform.prepend(this.scaleMatrix(arrayChild));
                  }
                  break;
               case "matrix":
                  m = this.array2matrix(arrayChild,this.yUp,this.scaling);
                  _transform.prepend(m);
                  break;
               case "node":
                  if(_objectData is MeshData)
                  {
                     this.parseNode(childNode,parent as ContainerData);
                  }
                  else
                  {
                     this.parseNode(childNode,_objectData as ContainerData);
                  }
                  break;
               case "instance_node":
                  this.parseNode(this.collada["library_nodes"].node.(@id == getId(childNode.@url))[0],_objectData as ContainerData);
                  break;
               case "instance_geometry":
                  if(String(childNode).indexOf("lines") == -1)
                  {
                     for each(instance_material in childNode..instance_material)
                     {
                        this.parseMaterial(instance_material.@symbol,this.getId(instance_material.@target));
                     }
                     geo = this.collada["library_geometries"].geometry.(@id == getId(childNode.@url))[0];
                     (_objectData as MeshData).geometry = geometryLibrary.addGeometry(geo.@id,geo);
                  }
                  break;
               case "instance_controller":
                  for each(instance_material in childNode..instance_material)
                  {
                     this.parseMaterial(instance_material.@symbol,this.getId(instance_material.@target));
                  }
                  ctrlr = this.collada["library_controllers"].controller.(@id == getId(childNode.@url))[0];
                  geo = this.collada["library_geometries"].geometry.(@id == getId(ctrlr["skin"][0].@source))[0];
                  (_objectData as MeshData).geometry = geometryLibrary.addGeometry(geo.@id,geo,ctrlr);
                  (_objectData as MeshData).skeleton = this.getId(childNode["skeleton"]);
            }
         }
      }
      
      private function parseMaterial(param1:String, param2:String) : void
      {
         default xml namespace = this.collada.namespace();
         var _loc3_:MaterialData = materialLibrary.addMaterial(param2);
         _symbolLibrary[param1] = _loc3_;
         if(param1 == "FrontColorNoCulling")
         {
            _loc3_.materialType = MaterialData.SHADING_MATERIAL;
         }
         else
         {
            _loc3_.textureFileName = this.getTextureFileName(param2);
            if(_loc3_.textureFileName)
            {
               _loc3_.materialType = MaterialData.TEXTURE_MATERIAL;
            }
            else
            {
               if(this.shading)
               {
                  _loc3_.materialType = MaterialData.SHADING_MATERIAL;
               }
               else
               {
                  _loc3_.materialType = MaterialData.COLOR_MATERIAL;
               }
               this.parseColorMaterial(param2,_loc3_);
            }
         }
      }
      
      private function parseGeometryData(param1:GeometryData) : void
      {
         var jointId:String;
         var verticesDictionary:Dictionary = null;
         var trianglesXMLList:XMLList = null;
         var isC4D:Boolean = false;
         var triangles:XML = null;
         var skin:XML = null;
         var tmp:String = null;
         var nameArray:Array = null;
         var bind_shape:Matrix3D = null;
         var bindMatrixId:String = null;
         var float_array:Array = null;
         var v:Array = null;
         var matrix:Matrix3D = null;
         var name:String = null;
         var skinController:SkinController = null;
         var i:int = 0;
         var weightsId:String = null;
         var weights:Array = null;
         var vcount:Array = null;
         var skinVertex:SkinVertex = null;
         var c:int = 0;
         var count:int = 0;
         var field:Array = null;
         var input:XML = null;
         var data:Array = null;
         var s:String = null;
         var arr:Array = null;
         var t:int = 0;
         var len:Number = NaN;
         var symbol:String = null;
         var _meshMaterialData:MeshMaterialData = null;
         var j:Number = NaN;
         var semantic:String = null;
         var _faceData:FaceData = null;
         var vn:Number = NaN;
         var fld:String = null;
         var _vertex:Vertex = null;
         var geometryData:GeometryData = param1;
         default xml namespace = this.collada.namespace();
         Debug.trace(" + Parse Geometry : " + geometryData.name);
         verticesDictionary = new Dictionary(true);
         trianglesXMLList = geometryData.geoXML["mesh"].triangles;
         isC4D = trianglesXMLList.length() == 0 && geometryData.geoXML["mesh"].polylist.length() > 0;
         if(!trianglesXMLList.length())
         {
            if(geometryData.geoXML["mesh"].polylist.length())
            {
               trianglesXMLList = geometryData.geoXML["mesh"].polylist;
            }
            else if(geometryData.geoXML["mesh"].polygons.length())
            {
               trianglesXMLList = geometryData.geoXML["mesh"].polygons;
            }
         }
         for each(triangles in trianglesXMLList)
         {
            field = [];
            for each(input in triangles["input"])
            {
               semantic = input.@semantic;
               switch(semantic)
               {
                  case "VERTEX":
                     this.deserialize(input,geometryData.geoXML,Vertex,geometryData.vertices);
                     break;
                  case "TEXCOORD":
                     this.deserialize(input,geometryData.geoXML,UV,geometryData.uvs);
               }
               field.push(input.@semantic);
            }
            data = [];
            for each(s in triangles["p"])
            {
               arr = this.getNumberArray(s);
               for each(t in arr)
               {
                  data.push(t);
               }
            }
            len = Number(triangles.@count);
            symbol = triangles.@material;
            Debug.trace(" + Parse MeshMaterialData");
            _meshMaterialData = new MeshMaterialData();
            _meshMaterialData.symbol = symbol;
            geometryData.materials.push(_meshMaterialData);
            j = 0;
            while(j < len)
            {
               _faceData = new FaceData();
               vn = 0;
               while(vn < 3)
               {
                  for each(fld in field)
                  {
                     switch(fld)
                     {
                        case "VERTEX":
                           _faceData["v" + vn] = data.shift();
                           break;
                        case "TEXCOORD":
                           _faceData["uv" + vn] = data.shift();
                           break;
                        default:
                           data.shift();
                     }
                  }
                  vn++;
               }
               verticesDictionary[_faceData.v0] = geometryData.vertices[_faceData.v0];
               verticesDictionary[_faceData.v1] = geometryData.vertices[_faceData.v1];
               verticesDictionary[_faceData.v2] = geometryData.vertices[_faceData.v2];
               _meshMaterialData.faceList.push(geometryData.faces.length);
               geometryData.faces.push(_faceData);
               j++;
            }
         }
         if(centerMeshes)
         {
            geometryData.maxX = -Infinity;
            geometryData.minX = Infinity;
            geometryData.maxY = -Infinity;
            geometryData.minY = Infinity;
            geometryData.maxZ = -Infinity;
            geometryData.minZ = Infinity;
            for each(_vertex in verticesDictionary)
            {
               if(geometryData.maxX < _vertex.arcane::_x)
               {
                  geometryData.maxX = _vertex.arcane::_x;
               }
               if(geometryData.minX > _vertex.arcane::_x)
               {
                  geometryData.minX = _vertex.arcane::_x;
               }
               if(geometryData.maxY < _vertex.arcane::_y)
               {
                  geometryData.maxY = _vertex.arcane::_y;
               }
               if(geometryData.minY > _vertex.arcane::_y)
               {
                  geometryData.minY = _vertex.arcane::_y;
               }
               if(geometryData.maxZ < _vertex.arcane::_z)
               {
                  geometryData.maxZ = _vertex.arcane::_z;
               }
               if(geometryData.minZ > _vertex.arcane::_z)
               {
                  geometryData.minZ = _vertex.arcane::_z;
               }
            }
         }
         if(String(geometryData.geoXML["extra"].technique.double_sided) != "")
         {
            geometryData.bothsides = geometryData.geoXML["extra"].technique.double_sided[0].toString() == "1";
         }
         else
         {
            geometryData.bothsides = false;
         }
         if(!geometryData.ctrlXML)
         {
            return;
         }
         skin = geometryData.ctrlXML["skin"][0];
         jointId = this.getId(skin["joints"].input.(@semantic == "JOINT")[0].@source);
         tmp = skin["source"].(@id == jointId)["Name_array"].toString();
         if(!tmp)
         {
            tmp = skin["source"].(@id == jointId)["IDREF_array"].toString();
         }
         tmp = tmp.replace(/\n/g," ");
         nameArray = this.getStringArray(tmp);
         bind_shape = this.array2matrix(this.getNumberArray(skin["bind_shape_matrix"][0].toString()),this.yUp,this.scaling);
         bindMatrixId = this.getId(skin["joints"].input.(@semantic == "INV_BIND_MATRIX").@source);
         float_array = this.getNumberArray(skin["source"].(@id == bindMatrixId)[0].float_array.toString());
         i = 0;
         while(i < float_array.length)
         {
            name = nameArray[i / 16];
            matrix = this.array2matrix(float_array.slice(i,i + 16),this.yUp,this.scaling);
            matrix.prepend(bind_shape);
            geometryData.skinControllers.push(skinController = new SkinController());
            skinController.name = name;
            skinController.bindMatrix = matrix;
            this._skinControllers.push(skinController);
            i += 16;
         }
         Debug.trace(" + SkinWeight");
         tmp = skin["vertex_weights"][0].@count;
         weightsId = this.getId(skin["vertex_weights"].input.(@semantic == "WEIGHT")[0].@source);
         tmp = skin["source"].(@id == weightsId)["float_array"].toString();
         weights = this.getNumberArray(tmp);
         tmp = skin["vertex_weights"].vcount.toString();
         vcount = this.getIntArray(tmp);
         tmp = skin["vertex_weights"].v.toString();
         v = this.getIntArray(tmp);
         count = 0;
         i = 0;
         while(i < geometryData.vertices.length)
         {
            c = int(vcount[i]);
            skinVertex = new SkinVertex(geometryData.vertices[i]);
            geometryData.vertices[i].skinVertex = skinVertex;
            geometryData.skinVertices.push(skinVertex);
            for each(skinController in geometryData.skinControllers)
            {
               skinController.skinVertices.push(skinVertex);
            }
            j = 0;
            while(j < c)
            {
               skinVertex.controllers.push(geometryData.skinControllers[v[count]]);
               count++;
               skinVertex.weights.push(weights[v[count]]);
               count++;
               j++;
            }
            i++;
         }
      }
      
      private function parseAnimationClips() : void
      {
         var _loc4_:ChannelData = null;
         var _loc5_:XML = null;
         var _loc6_:XML = null;
         default xml namespace = this.collada.namespace();
         var _loc1_:XML = this.collada["library_animations"][0];
         if(!_loc1_)
         {
            Debug.trace(" ! ------------- No animations to parse -------------");
            return;
         }
         var _loc2_:XML = this.collada["library_animation_clips"][0];
         Debug.trace(" ! Animation Clips Exist : " + this._haveClips);
         Debug.trace(" ! ------------- Begin Parse Animation -------------");
         var _loc3_:uint = 0;
         if(_loc1_["animation"]["animation"].length() == 0)
         {
            for each(_loc5_ in _loc1_["animation"])
            {
               if(String(_loc5_.@id).length > 0)
               {
                  this.channelLibrary.addChannel(_loc5_.@id,_loc5_);
               }
               else
               {
                  Debug.trace(" ! COLLADAMax2009 id : _" + _loc3_);
                  this.channelLibrary.addChannel("_" + String(_loc3_++),_loc5_);
               }
            }
         }
         for each(_loc5_ in _loc1_["animation"]["animation"])
         {
            if(String(_loc5_.@id).length > 0)
            {
               this.channelLibrary.addChannel(_loc5_.@id,_loc5_);
            }
            else
            {
               Debug.trace(" ! C4D id : _" + _loc3_);
               this.channelLibrary.addChannel("_" + String(_loc3_++),_loc5_);
            }
         }
         if(_loc2_)
         {
            for each(_loc6_ in _loc2_["animation_clip"])
            {
               this.parseAnimationClip(_loc6_);
            }
         }
         this._defaultAnimationClip = this.animationLibrary.addAnimation("default");
         this._defaultAnimationClip.animationType = AnimationDataType.SKIN_ANIMATION;
         for each(_loc4_ in this.channelLibrary)
         {
            this._defaultAnimationClip.channels[_loc4_.name] = _loc4_;
         }
         Debug.trace(" ! ------------- End Parse Animation -------------");
         this._channelArray = this.channelLibrary.getChannelArray();
         this._channelArrayLength = this._channelArray.length;
         _totalChunks += this._channelArrayLength;
      }
      
      private function parseAnimationClip(param1:XML) : void
      {
         var _loc3_:XML = null;
         default xml namespace = this.collada.namespace();
         Debug.trace(" + Parse Animation : " + param1.@id);
         var _loc2_:AnimationData = this.animationLibrary.addAnimation(param1.@id);
         _loc2_.animationType = AnimationDataType.SKIN_ANIMATION;
         for each(_loc3_ in param1["instance_animation"])
         {
            _loc2_.channels[this.getId(_loc3_.@url)] = this.channelLibrary[this.getId(_loc3_.@url)];
         }
      }
      
      private function parseChannelData(param1:ChannelData) : void
      {
         var node:XML;
         var id:String;
         var name:String;
         var type:String;
         var sampler:XML;
         var channel:Channel;
         var i:int = 0;
         var j:int = 0;
         var input:XML = null;
         var src:XML = null;
         var list:Array = null;
         var len:int = 0;
         var stride:int = 0;
         var semantic:String = null;
         var p:String = null;
         var channelData:ChannelData = param1;
         default xml namespace = this.collada.namespace();
         node = channelData.xml;
         id = node["channel"].@target;
         name = id.split("/")[0];
         type = id.split("/")[1];
         sampler = node["sampler"][0];
         if(!type)
         {
            Debug.trace(" ! No animation type detected");
            return;
         }
         if(String(node.@id).length > 0 && (type.split(".").length == 1 || type.split(".")[1].length > 1))
         {
            type = type.split(".")[0];
            if(type == "image" || String(node.@id).split(".")[1] == "frameExtension")
            {
               Debug.trace(" ! Material animation not yet implemented");
               return;
            }
         }
         else if(type.split(".")[1] == "ANGLE")
         {
            type = type.split(".")[0];
         }
         else
         {
            type = type.split(".").join("");
         }
         channel = channelData.channel = new Channel(name);
         this._defaultAnimationClip.channels[channelData.name] = channelData;
         Debug.trace(" ! channelType : " + type);
         for each(input in sampler["input"])
         {
            src = node["source"].(@id == getId(input.@source))[0];
            list = this.getNumberArray(String(src["float_array"]));
            len = int(src["technique_common"].accessor.@count);
            stride = int(src["technique_common"].accessor.@stride);
            semantic = input.@semantic;
            if(stride == 0)
            {
               stride = 1;
            }
            switch(semantic)
            {
               case "INPUT":
                  for each(p in list)
                  {
                     channel.times.push(p);
                  }
                  if(this._defaultAnimationClip.start > channel.times[0])
                  {
                     this._defaultAnimationClip.start = channel.times[0];
                  }
                  if(this._defaultAnimationClip.end < channel.times[channel.times.length - 1])
                  {
                     this._defaultAnimationClip.end = channel.times[channel.times.length - 1];
                  }
                  break;
               case "OUTPUT":
                  i = 0;
                  while(i < len)
                  {
                     channel.param[i] = new Array();
                     if(stride == 16)
                     {
                        channel.param[i].push(this.array2matrix(list.slice(i * stride,i * stride + 16),this.yUp,this.scaling));
                     }
                     else
                     {
                        j = 0;
                        while(j < stride)
                        {
                           channel.param[i].push(list[i * stride + j]);
                           j++;
                        }
                     }
                     i++;
                  }
                  Debug.trace("OUTPUT:" + len);
                  break;
               case "INTERPOLATION":
                  for each(p in list)
                  {
                     channel.interpolations.push(p);
                  }
                  break;
               case "IN_TANGENT":
                  i = 0;
                  while(i < len)
                  {
                     channel.inTangent[i] = new Vector.<Point>();
                     j = 0;
                     while(j < stride)
                     {
                        channel.inTangent[i].push(new Point(list[stride * i + j],list[stride * i + j + 1]));
                        j++;
                     }
                     i++;
                  }
                  break;
               case "OUT_TANGENT":
                  i = 0;
                  while(i < len)
                  {
                     channel.outTangent[i] = new Vector.<Point>();
                     j = 0;
                     while(j < stride)
                     {
                        channel.outTangent[i].push(new Point(list[stride * i + j],list[stride * i + j + 1]));
                        j++;
                     }
                     i++;
                  }
            }
         }
         channelData.type = type;
      }
      
      private function getTextureFileName(materialName:String) : String
      {
         var ns:Namespace = this.collada.namespace();
         var material:XML = findElement(this.collada.elements(new QName(ns,"library_materials")).elements(new QName(ns,"material")),"id",materialName);
         if(material == null) return null;
         var effectId:String = getId(String(material.elements(new QName(ns,"instance_effect")).attribute(new QName("","url"))));
         var effect:XML = findElement(this.collada.elements(new QName(ns,"library_effects")).elements(new QName(ns,"effect")),"id",effectId);
         if(effect == null) return null;
         var textures:XMLList = effect.descendants(new QName(ns,"texture"));
         if(textures.length() == 0) return null;
         var imageId:String = String(textures[0].attribute(new QName("","texture")));
         var params:XMLList = effect.descendants(new QName(ns,"newparam"));
         var sampler:XML = findElement(params,"sid",imageId);
         if(sampler != null)
         {
            var sourceId:String = String(sampler.descendants(new QName(ns,"source"))[0]);
            var surface:XML = findElement(params,"sid",sourceId);
            if(surface != null) imageId = String(surface.descendants(new QName(ns,"init_from"))[0]);
         }
         var image:XML = findElement(this.collada.elements(new QName(ns,"library_images")).elements(new QName(ns,"image")),"id",imageId);
         if(image == null) return null;
         var filename:String = String(image.elements(new QName(ns,"init_from")));
         return filename.substr(0,2) == "./" ? filename.substr(2) : filename;
      }

      private function findElement(elements:XMLList, attributeName:String, value:String) : XML
      {
         for each(var element:XML in elements)
         {
            if(String(element.attribute(new QName("",attributeName))) == value) return element;
         }
         return null;
      }

      private function parseColorMaterial(param1:String, param2:MaterialData) : void
      {
         var material:XML = null;
         var effectId:String = null;
         var effect:XML = null;
         var colorName:String = param1;
         var materialData:MaterialData = param2;
         default xml namespace = this.collada.namespace();
         material = this.collada["library_materials"].material.(@id == colorName)[0];
         if(material)
         {
            effectId = this.getId(material["instance_effect"].@url);
            effect = this.collada["library_effects"].effect.(@id == effectId)[0];
            materialData.ambientColor = this.getColorValue(effect..ambient[0]);
            materialData.diffuseColor = this.getColorValue(effect..diffuse[0]);
            materialData.specularColor = this.getColorValue(effect..specular[0]);
            materialData.shininess = Number(effect..shininess.float[0]);
         }
      }
      
      private function getColorValue(param1:XML) : uint
      {
         default xml namespace = this.collada.namespace();
         if(!param1 || param1.length() == 0)
         {
            return 16777215;
         }
         if(!param1["color"] || param1["color"].length() == 0)
         {
            return 16777215;
         }
         var _loc2_:Array = String(param1["color"]).split(" ");
         if(_loc2_.length <= 0)
         {
            return 16777215;
         }
         return int(_loc2_[0] * 255 << 16) | int(_loc2_[1] * 255 << 8) | int(_loc2_[2] * 255);
      }
      
      private function array2matrix(param1:Array, param2:Boolean, param3:Number) : Matrix3D
      {
         default xml namespace = this.collada.namespace();
         var _loc4_:Matrix3D = new Matrix3D();
         var _loc5_:Vector.<Number> = new Vector.<Number>(16,true);
         if(param1.length >= 12)
         {
            if(param2)
            {
               _loc5_[0] = param1[0];
               _loc5_[4] = -param1[1];
               _loc5_[8] = -param1[2];
               _loc5_[12] = -param1[3] * param3;
               _loc5_[1] = -param1[4];
               _loc5_[5] = param1[5];
               _loc5_[9] = param1[6];
               _loc5_[13] = param1[7] * param3;
               _loc5_[2] = -param1[8];
               _loc5_[6] = param1[9];
               _loc5_[10] = param1[10];
               _loc5_[14] = param1[11] * param3;
            }
            else
            {
               _loc5_[0] = param1[0];
               _loc5_[8] = param1[1];
               _loc5_[4] = param1[2];
               _loc5_[12] = param1[3] * param3;
               _loc5_[2] = param1[4];
               _loc5_[10] = param1[5];
               _loc5_[6] = param1[6];
               _loc5_[14] = param1[7] * param3;
               _loc5_[1] = param1[8];
               _loc5_[9] = param1[9];
               _loc5_[5] = param1[10];
               _loc5_[13] = param1[11] * param3;
            }
         }
         if(param1.length >= 16)
         {
            _loc5_[3] = param1[12];
            _loc5_[7] = param1[13];
            _loc5_[11] = param1[14];
            _loc5_[15] = param1[15];
         }
         else
         {
            _loc5_[3] = 0;
            _loc5_[7] = 0;
            _loc5_[11] = 0;
            _loc5_[15] = 1;
         }
         _loc4_.rawData = _loc5_;
         return _loc4_;
      }
      
      private function deserialize(param1:XML, param2:XML, param3:Class, param4:Array) : Array
      {
         var id:String = null;
         var acc:XMLList = null;
         var floId:String = null;
         var floXML:XMLList = null;
         var floStr:String = null;
         var floats:Array = null;
         var float:Number = NaN;
         var params:Array = null;
         var param:String = null;
         var par:XML = null;
         var len:int = 0;
         var i:int = 0;
         var element:ValueObject = null;
         var vertex:Vertex = null;
         var uv:UV = null;
         var recursive:XMLList = null;
         var input:XML = param1;
         var geo:XML = param2;
         var VObject:Class = param3;
         var output:Array = param4;
         default xml namespace = this.collada.namespace();
         var ns:Namespace = this.collada.namespace();
         id = this.getId(String(input.attribute(new QName("","source"))));
         var sourceElement:XML = findElement(geo.descendants(new QName(ns,"source")),"id",id);
         acc = sourceElement != null ? sourceElement.elements(new QName(ns,"technique_common")).elements(new QName(ns,"accessor")) : new XMLList();
         if(acc.length() > 0)
         {
            floId = this.getId(String(acc.attribute(new QName("","source"))));
            var floatElement:XML = findElement(this.collada.descendants(new QName(ns,"float_array")),"id",floId);
            if(floatElement == null) throw new Error("Missing COLLADA float array: " + floId);
            floXML = new XMLList(floatElement);
            floStr = floXML.toString();
            floats = this.getNumberArray(floStr);
            params = [];
            for each(par in acc.elements(new QName(ns,"param")))
            {
               params.push(String(par.attribute(new QName("","name"))));
            }
            len = int(floats.length);
            i = 0;
            while(i < len)
            {
               element = new VObject();
               if(element is Vertex)
               {
                  vertex = element as Vertex;
                  for each(param in params)
                  {
                     float = Number(floats[i]);
                     switch(param)
                     {
                        case this.VALUE_X:
                           if(this.yUp)
                           {
                              vertex.arcane::_x = -float * this.scaling;
                           }
                           else
                           {
                              vertex.arcane::_x = float * this.scaling;
                           }
                           break;
                        case this.VALUE_Y:
                           vertex.arcane::_y = float * this.scaling;
                           break;
                        case this.VALUE_Z:
                           vertex.arcane::_z = float * this.scaling;
                     }
                     i++;
                  }
               }
               else if(element is UV)
               {
                  uv = element as UV;
                  for each(param in params)
                  {
                     float = Number(floats[i]);
                     switch(param)
                     {
                        case this.VALUE_U:
                           uv.arcane::_u = float;
                           break;
                        case this.VALUE_V:
                           uv.arcane::_v = float;
                     }
                     i++;
                  }
               }
               output.push(element);
            }
         }
         else
         {
            var verticesElement:XML = findElement(geo.descendants(new QName(ns,"vertices")),"id",id);
            if(verticesElement == null) throw new Error("Missing COLLADA vertex source: " + id + " input=" + input.toXMLString());
            recursive = verticesElement.elements(new QName(ns,"input"));
            output = this.deserialize(recursive[0],geo,VObject,output);
         }
         return output;
      }
   }
}

