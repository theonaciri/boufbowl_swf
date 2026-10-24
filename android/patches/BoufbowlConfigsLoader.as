package com.ankamagames.boufbowl.client.application.loading
{
   import com.ankamagames.xgaming.utils.load.URLQueueLoader;
   import com.ankamagames.xgaming.utils.load.event.URLQueueLoaderEvent;
   import com.ankamagames.xgaming.utils.string.StringUtils;
   import flash.net.URLRequest;
   import flash.text.TextField;
   import flash.text.TextFormat;
   
   public class BoufbowlConfigsLoader extends URLQueueLoader
   {
      
      private static const LOAD_ID_CONFIG:uint = 1;
      
      private static const LOAD_ID_LANG:uint = 2;
      
      private static const LOAD_ID_SOUND:uint = 3;
      
      private static const LOAD_ID_STADIUMS:uint = 4;
      
      private static const LOAD_ID_MOTD:uint = 5;
      
      private var _errorField:TextField;
      
      private var _configFileData:String;
      
      private var _langFileData:String;
      
      private var _soundFileData:String;
      
      private var _stadiumsFileData:String;
      
      private var _motdFileData:String;
      
      public function BoufbowlConfigsLoader(errorField:TextField)
      {
         super();
         this._errorField = errorField;
         this._errorField.embedFonts = false;
         this._errorField.defaultTextFormat = new TextFormat("_sans",16,0xffffff);
         this.init();
      }
      
      public function get configFileData() : String
      {
         return this._configFileData;
      }
      
      public function get langFileData() : String
      {
         return this._langFileData;
      }
      
      public function get soundFileData() : String
      {
         return this._soundFileData;
      }
      
      public function get stadiumsFileData() : String
      {
         return this._stadiumsFileData;
      }
      
      public function get motdFileData() : String
      {
         return this._motdFileData;
      }
      
      override public function startLoading() : void
      {
         super.startLoading();
      }
      
      private function init() : void
      {
         addEventListener(URLQueueLoader.LOAD_ERROR,this.configLoadErrorHandler,false,0,true);
         addEventListener(URLQueueLoader.LOAD_COMPLETE,this.configLoadCompleteHandler,false,0,true);
         push(LOAD_ID_CONFIG,new URLRequest("app:/resources/config.json"));
         push(LOAD_ID_LANG,new URLRequest("app:/resources/lang.json"));
         push(LOAD_ID_SOUND,new URLRequest("app:/resources/sound.json"));
         push(LOAD_ID_STADIUMS,new URLRequest("app:/resources/stadiums.json"));
         push(LOAD_ID_MOTD,new URLRequest("app:/resources/motd.json"));
      }
      
      private function configLoadCompleteHandler(param1:URLQueueLoaderEvent) : void
      {
         switch(param1.id)
         {
            case LOAD_ID_CONFIG:
               this._configFileData = param1.data;
               break;
            case LOAD_ID_LANG:
               this._langFileData = param1.data;
               break;
            case LOAD_ID_SOUND:
               this._soundFileData = param1.data;
               break;
            case LOAD_ID_STADIUMS:
               this._stadiumsFileData = param1.data;
               break;
            case LOAD_ID_MOTD:
               this._motdFileData = param1.data;
               break;
            default:
               throw new Error("Bad loading management.");
         }
      }
      
      private function configLoadErrorHandler(event:URLQueueLoaderEvent) : void
      {
         this._errorField.text = "Boufbowl Fan — configuration unavailable\n" + event.errorMessage + "\n" + "File name : " + StringUtils.getFileName(event.url.url);
      }
   }
}

