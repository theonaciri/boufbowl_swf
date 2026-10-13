package com.ankamagames.boufbowl.client.application
{
   import as3.collections.ArrayList;
   import as3.collections.IList;
   import as3.collections.IMap;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.xgaming.utils.config.JSONConfig;
   
   public class BoufbowlConfig extends JSONConfig implements IBoufbowlConfig
   {
      
      private var _version:String;
      
      private var _debugMode:Boolean;
      
      private var _displayUncaughtError:Boolean;
      
      private var _assetsPreloadingEnabled:Boolean;
      
      private var _premiumServiceEnabled:Boolean;
      
      private var _soundBasePath:String;
      
      private var _tiphonPath:String;
      
      private var _soundEnabled:Boolean;
      
      private var _soundMasterVolume:Number;
      
      private var _serverPassLoginMethodEnabled:Boolean;
      
      private var _serverHost:String;
      
      private var _serverPort:int;
      
      private var _showStats:Boolean;
      
      private var _chronoEnabled:Boolean;
      
      private var _chronoPlacementDuration:int;
      
      private var _chronoFirstTurnDuration:int;
      
      private var _chronoTurnDuration:int;
      
      private var _3dActivated:Boolean;
      
      private var _facebookEnabled:Boolean;
      
      private var _facebookAppId:String;
      
      private var _facebookChannelUrl:String;
      
      private var _facebookCanvasUrl:String;
      
      private var _facebookPermissions:IList;
      
      private var _optionsVisibility:IMap;
      
      public function BoufbowlConfig(param1:String)
      {
         super(param1);
      }
      
      public function get version() : String
      {
         return this._version;
      }
      
      public function get debugMode() : Boolean
      {
         return this._debugMode;
      }
      
      public function get displayUncaughtError() : Boolean
      {
         return this._displayUncaughtError;
      }
      
      public function set displayUncaughtError(param1:Boolean) : void
      {
         this._displayUncaughtError = param1;
      }
      
      public function get assetsPreloadingEnabled() : Boolean
      {
         return this._assetsPreloadingEnabled;
      }
      
      public function get premiumServiceEnabled() : Boolean
      {
         return this._premiumServiceEnabled;
      }
      
      public function get fxsFile() : String
      {
         return "app:/assets/fx/fx.swf";
      }
      
      public function get onomatopoeiasFile() : String
      {
         return "app:/assets/fx/onomatopoeia.swf";
      }
      
      public function get moviesFile() : String
      {
         return "app:/assets/artworks/movies.swf";
      }
      
      public function get animatedCutscenesFile() : String
      {
         return "app:/assets/artworks/cutscenes-animated.swf";
      }
      
      public function get illustrationCutscenesFile() : String
      {
         return "app:/assets/artworks/cutscene-illustration.swf";
      }
      
      public function get cutscenesBoufbowlerRepositoryFile() : String
      {
         return "app:/assets/artworks/cutscene-boufbowler-repository.swf";
      }
      
      public function get pomPomGirlCutscenesFile() : String
      {
         return "app:/assets/artworks/cutscene-pompom.swf";
      }
      
      public function get versusCutsceneFile() : String
      {
         return "app:/assets/artworks/cutscene-versus.swf";
      }
      
      public function get tutoStrategicHelpFile() : String
      {
         return "app:/assets/artworks/tuto-strategic-help.swf";
      }
      
      public function get soundBasePath() : String
      {
         return this._soundBasePath;
      }
      
      public function get tiphonPath() : String
      {
         return this._tiphonPath;
      }
      
      public function get tiphonBonesPath() : String
      {
         return this._tiphonPath + "/bones/";
      }
      
      public function get tiphonIndexPath() : String
      {
         return this._tiphonPath + "/bones/index.xml";
      }
      
      public function get tiphonSkinsPath() : String
      {
         return this._tiphonPath + "/skins/";
      }
      
      public function get soundEnabled() : Boolean
      {
         return this._soundEnabled;
      }
      
      public function set soundEnabled(param1:Boolean) : void
      {
         this._soundEnabled = param1;
      }
      
      public function get soundMasterVolume() : Number
      {
         return this._soundMasterVolume;
      }
      
      public function set soundMasterVolume(param1:Number) : void
      {
         this._soundMasterVolume = param1;
      }
      
      public function get serverPassLoginMethodEnabled() : Boolean
      {
         return this._serverPassLoginMethodEnabled;
      }
      
      public function get serverHost() : String
      {
         return this._serverHost;
      }
      
      public function set serverHost(param1:String) : void
      {
         this._serverHost = param1;
      }
      
      public function get serverPort() : int
      {
         return this._serverPort;
      }
      
      public function set serverPort(param1:int) : void
      {
         this._serverPort = param1;
      }
      
      public function get showStats() : Boolean
      {
         return this._showStats;
      }
      
      public function set showStats(param1:Boolean) : void
      {
         this._showStats = param1;
      }
      
      public function get chronoEnabled() : Boolean
      {
         return this._chronoEnabled;
      }
      
      public function set chronoEnabled(param1:Boolean) : void
      {
         this._chronoEnabled = param1;
      }
      
      public function get chronoPlacementDuration() : int
      {
         return this._chronoPlacementDuration;
      }
      
      public function get chronoFirstTurnDuration() : int
      {
         return this._chronoFirstTurnDuration;
      }
      
      public function set chronoFirstTurnDuration(param1:int) : void
      {
         this._chronoFirstTurnDuration = param1;
      }
      
      public function get chronoTurnDuration() : int
      {
         return this._chronoTurnDuration;
      }
      
      public function set chronoTurnDuration(param1:int) : void
      {
         this._chronoTurnDuration = param1;
      }
      
      public function get activate3DScene() : Boolean
      {
         return this._3dActivated;
      }
      
      public function set activate3DScene(param1:Boolean) : void
      {
         this._3dActivated = param1;
      }
      
      public function get optionsVisibility() : IMap
      {
         return this._optionsVisibility;
      }
      
      public function get facebookEnabled() : Boolean
      {
         return this._facebookEnabled;
      }
      
      public function get facebookAppId() : String
      {
         return this._facebookAppId;
      }
      
      public function get facebookChannelUrl() : String
      {
         return this._facebookChannelUrl;
      }
      
      public function get facebookCanvasUrl() : String
      {
         return this._facebookCanvasUrl;
      }
      
      public function get facebookPermissions() : IList
      {
         return this._facebookPermissions;
      }
      
      override protected function decoded(param1:Object) : void
      {
         this._version = getString(param1,["version"],"Unknown");
         this._debugMode = getBoolean(param1,["debugMode"],false);
         this._displayUncaughtError = getBoolean(param1,["displayUncaughtError"],true);
         this._assetsPreloadingEnabled = getBoolean(param1,["assetsPreloadingEnabled"],true);
         this._premiumServiceEnabled = getBoolean(param1,["premiumServiceEnabled"],true);
         this._soundBasePath = getString(param1,["soundBasePath"],"app:/assets/sounds/");
         this._tiphonPath = getString(param1,["tiphonBasePath"],"app:/assets/sprites");
         this._soundEnabled = getBoolean(param1,["sound","enabled"],true);
         this._soundMasterVolume = getNumber(param1,["sound","masterVolume"],1);
         this._serverPassLoginMethodEnabled = getBoolean(param1,["server","passLoginMethodEnabled"],false);
         this._serverHost = getString(param1,["server","host"],"localhost");
         this._serverPort = getInt(param1,["server","port"],9991);
         this._showStats = getBoolean(param1,["showStats"],false);
         this._chronoEnabled = getBoolean(param1,["chrono","enabled"],true);
         this._chronoPlacementDuration = getInt(param1,["chrono","placementDuration"],60);
         this._chronoFirstTurnDuration = getInt(param1,["chrono","firstTurnDuration"],600);
         this._chronoTurnDuration = getInt(param1,["chrono","turnDuration"],120);
         this._3dActivated = getBoolean(param1,["3dActivated"],true);
         this._facebookEnabled = getBoolean(param1,["facebookEnabled"],false);
         this._facebookAppId = getString(param1,["facebookAppId"],"");
         this._facebookChannelUrl = getString(param1,["facebookChannelUrl"],"");
         this._facebookCanvasUrl = getString(param1,["facebookCanvasUrl"],"");
         this._facebookPermissions = getStringArray(param1,["facebookPermissions"],null);
         if(this._facebookPermissions == null)
         {
            this._facebookPermissions == new ArrayList();
         }
         this._optionsVisibility = getBooleanMap(param1,["optionsVisibility"],null);
         if(this._optionsVisibility == null)
         {
            throw new Error("JSon config must have defined \'optionsVisibility\' map.");
         }
      }
   }
}

