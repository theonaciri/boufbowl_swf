package com.ankamagames.jerakine.types
{
   import com.ankamagames.jerakine.enum.OperatingSystem;
   import com.ankamagames.jerakine.noAir.File;
   import com.ankamagames.jerakine.utils.crypto.CRC32;
   import com.ankamagames.jerakine.utils.system.SystemManager;
   import flash.errors.IllegalOperationError;
   import flash.system.LoaderContext;
   import flash.utils.ByteArray;
   import flash.utils.Dictionary;

   public class Uri
   {

      public static var MEMORY_LOG:Dictionary = new Dictionary(true);

      // Numbered captures avoid PCRE named groups and branch-reset syntax
      // that the browser emulator does not support. Preserve path|subpath.
      private static const URI_SYNTAX:RegExp = /^(?:([a-z]+):\/\/)?([^|]*)(?:\|\/?(.*))?$/i;

      private var _protocol:String;

      private var _path:String;

      private var _subpath:String;

      private var _tag:*;

      private var _sum:String;

      private var _loaderContext:LoaderContext;

      public function Uri(param1:String = null)
      {
         super();
         if(Boolean(param1) && param1.length > 0)
         {
            this.parseUri(param1);
         }
         MEMORY_LOG[this] = 1;
      }

      public function get protocol() : String
      {
         return this._protocol;
      }

      public function set protocol(param1:String) : void
      {
         this._protocol = param1;
         this._sum = "";
      }

      public function get path() : String
      {
         return this._path;
      }

      public function set path(param1:String) : void
      {
         this._path = param1;
         this._sum = "";
      }

      public function get subPath() : String
      {
         return this._subpath;
      }

      public function set subPath(param1:String) : void
      {
         this._subpath = param1.substr(0,1) == "/" ? param1.substr(1) : param1;
         this._sum = "";
      }

      public function get uri() : String
      {
         return this.toString();
      }

      public function set uri(param1:String) : void
      {
         this.parseUri(param1);
      }

      public function get tag() : *
      {
         return this._tag;
      }

      public function set tag(param1:*) : void
      {
         this._tag = param1;
      }

      public function get loaderContext() : LoaderContext
      {
         return this._loaderContext;
      }

      public function set loaderContext(param1:LoaderContext) : void
      {
         this._loaderContext = param1;
      }

      public function get fileType() : String
      {
         if(!this._subpath || this._subpath.length == 0)
         {
            return this._path.substr(this._path.lastIndexOf(".") + 1);
         }
         return this._subpath.substr(this._subpath.lastIndexOf(".") + 1);
      }

      public function get fileName() : String
      {
         if(!this._subpath || this._subpath.length == 0)
         {
            return this._path.substr(this._path.lastIndexOf("/") + 1);
         }
         return this._subpath.substr(this._subpath.lastIndexOf("/") + 1);
      }

      public function get normalizedUri() : String
      {
         switch(this._protocol)
         {
            case "http":
            case "file":
            case "zip":
            case "upd":
            case "mod":
            case "d2p":
            case "pak":
               return this.replaceChar(this.uri,"\\","/");
            default:
               throw new IllegalOperationError("Unsupported protocol " + this._protocol + " for normalization.");
         }
      }

      public function toString(param1:Boolean = true) : String
      {
         return this._protocol + "://" + this._path + (Boolean(param1) && Boolean(this._subpath) && this._subpath.length > 0 ? "|" + this._subpath : "");
      }

      public function toSum() : String
      {
         if(this._sum.length > 0)
         {
            return this._sum;
         }
         var _loc1_:CRC32 = new CRC32();
         var _loc2_:ByteArray = new ByteArray();
         _loc2_.writeUTF(this.normalizedUri);
         _loc1_.update(_loc2_);
         return this._sum = _loc1_.getValue().toString(16);
      }

      public function toFile() : File
      {
         if(this._path.indexOf("\\\\") == 0 || this._path.charAt(1) == ":")
         {
            return new File(this._path);
         }
         return new File(File.applicationDirectory.nativePath + File.separator + this._path);
      }

      private function parseUri(param1:String) : void
      {
         var _loc2_:Array = param1.match(URI_SYNTAX);
         if(!_loc2_)
         {
            throw new ArgumentError("\'" + param1 + "\' is a misformated URI.");
         }
         this._protocol = (_loc2_[1] || "");
         if(this._protocol.length == 0)
         {
            this._protocol = "file";
         }
         if(SystemManager.getSingleton().os == OperatingSystem.WINDOWS)
         {
            this._path = _loc2_[2].replace("//","/");
         }
         else
         {
            this._path = _loc2_[2];
         }
         this._subpath = (_loc2_[3] || "");
         this._sum = "";
      }

      private function replaceChar(param1:String, param2:String, param3:String) : String
      {
         return param1.split(param2).join(param3);
      }
   }
}

