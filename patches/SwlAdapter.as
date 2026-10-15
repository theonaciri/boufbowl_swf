package com.ankamagames.jerakine.resources.adapters.impl
{
   import com.ankamagames.jerakine.pools.PoolableLoader;
   import com.ankamagames.jerakine.pools.PoolsManager;
   import com.ankamagames.jerakine.resources.ResourceErrorCode;
   import com.ankamagames.jerakine.resources.ResourceType;
   import com.ankamagames.jerakine.resources.adapters.AbstractUrlLoaderAdapter;
   import com.ankamagames.jerakine.resources.adapters.IAdapter;
   import com.ankamagames.jerakine.types.Swl;
   import flash.display.LoaderInfo;
   import flash.errors.EOFError;
   import flash.events.ErrorEvent;
   import flash.events.Event;
   import flash.events.IOErrorEvent;
   import flash.net.URLLoaderDataFormat;
   import flash.system.ApplicationDomain;
   import flash.system.LoaderContext;
   import flash.utils.ByteArray;

   public class SwlAdapter extends AbstractUrlLoaderAdapter implements IAdapter
   {

      private var _ldr:PoolableLoader;

      private var _onInit:Function;

      private var _swl:Swl;

      public function SwlAdapter()
      {
         super();
      }

      override protected function getResource(param1:String, param2:*) : *
      {
         return this._swl;
      }

      override protected function getResourceType() : uint
      {
         return ResourceType.RESOURCE_SWL;
      }

      override protected function process(param1:String, param2:*) : void
      {
         var loaderContext:LoaderContext;
         var file:uint = 0;
         var version:uint = 0;
         var frameRate:uint = 0;
         var classesCount:uint = 0;
         var classesList:Array = null;
         var i:uint = 0;
         var swfData:ByteArray = null;
         var dataFormat:String = param1;
         var data:* = param2;
         try
         {
            file = uint((data as ByteArray).readByte());
            if(file != 76)
            {
               dispatchFailure("Malformated library file (wrong header).",ResourceErrorCode.SWL_MALFORMED_LIBRARY);
               return;
            }
            version = uint((data as ByteArray).readByte());
            frameRate = (data as ByteArray).readUnsignedInt();
            classesCount = uint((data as ByteArray).readInt());
            classesList = new Array();
            i = 0;
            while(i < classesCount)
            {
               classesList.push((data as ByteArray).readUTF());
               i++;
            }
            swfData = new ByteArray();
            (data as ByteArray).readBytes(swfData);
         }
         catch(eof:EOFError)
         {
            dispatchFailure("Malformated library file (end of file).",ResourceErrorCode.SWL_MALFORMED_LIBRARY);
            return;
         }
         this._ldr = PoolsManager.getInstance().getLoadersPool().checkOut() as PoolableLoader;
         this._ldr.contentLoaderInfo.addEventListener(Event.COMPLETE,this._onInit = this.onLibraryInit(frameRate,classesList));
         this._ldr.contentLoaderInfo.addEventListener(IOErrorEvent.IO_ERROR,this.onLibraryError);
         loaderContext = getUri().loaderContext;
         if(!loaderContext)
         {
            // Each SWL owns its exported symbols. Explicit child domains and
            // COMPLETE avoid publishing a pooled loader before all definitions
            // have been initialized by the browser emulator.
            loaderContext = new LoaderContext(false,new ApplicationDomain(ApplicationDomain.currentDomain));
         }
         this._ldr.loadBytes(swfData,loaderContext);
      }

      override protected function getDataFormat() : String
      {
         return URLLoaderDataFormat.BINARY;
      }

      private function createResource(param1:uint, param2:Array, param3:ApplicationDomain) : void
      {
         this._swl = new Swl(param1,param2,param3);
         dispatchSuccess(null,null);
      }

      private function releaseLoader() : void
      {
         this._ldr.contentLoaderInfo.removeEventListener(Event.COMPLETE,this._onInit);
         this._ldr.contentLoaderInfo.removeEventListener(IOErrorEvent.IO_ERROR,this.onLibraryError);
         PoolsManager.getInstance().getLoadersPool().checkIn(this._ldr);
         this._ldr = null;
         this._onInit = null;
      }

      private function onLibraryInit(param1:uint, param2:Array) : Function
      {
         var frameRate:uint = param1;
         var classesList:Array = param2;
         return function(param1:Event):void
         {
            var _loc2_:* = (param1.target as LoaderInfo).applicationDomain;
            createResource(frameRate,classesList,_loc2_);
            releaseLoader();
         };
      }

      private function onLibraryError(param1:ErrorEvent) : void
      {
         dispatchFailure("Library loading from binaries failed: " + param1.text,ResourceErrorCode.SWL_MALFORMED_BINARY);
         this.releaseLoader();
      }
   }
}

