package com.ankamagames.xgaming.utils.flashvars
{
   import as3.collections.IMap;
   import as3.collections.Map;
   import com.ankamagames.xgaming.utils.display.stage.IStageWrapper;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.reider.log4AS3.ILogger;
   import flash.display.DisplayObject;
   import flash.net.SharedObject;
   import flash.errors.IllegalOperationError;
   
   public class FlashVarsManager
   {
      
      private static const LOGGER:ILogger = LoggerFactory.getLogger(FlashVarsManager);
      
      private var _flashVars:IMap;
      
      public function FlashVarsManager()
      {
         super();
      }
      
      public function init(param1:IStageWrapper) : void
      {
         var _loc3_:Object = null;
         var _loc4_:String = null;
         if(param1 == null)
         {
            throw new IllegalOperationError("\'stage\' parameter can\'t be null.");
         }
         this._flashVars = new Map();
         var _loc2_:DisplayObject = param1.stage.getChildAt(0);
         if(_loc2_ != null && _loc2_.loaderInfo != null)
         {
            _loc3_ = _loc2_.loaderInfo.parameters;
            for(_loc4_ in _loc3_)
            {
               this._flashVars.addItem(_loc4_,_loc3_[_loc4_]);
            }
         }
         else
         {
            LOGGER.warn("FlashVars can\'t be initialized. Stage\'s child is " + _loc2_ + ", root loaderInfo is " + (_loc2_ != null ? _loc2_.loaderInfo : null) + ".");
         }
      }
      
      public function getValue(param1:String) : String
      {
         if(this._flashVars == null)
         {
            throw new IllegalOperationError("\'init\' method must be called before!");
         }
         if(param1 == "lang" && this._flashVars.getItem("languageOverride") != "1")
         {
            var preferences:SharedObject=SharedObject.getLocal("BoufbowlPreferences","/");
            var language:String=String(preferences.data.language);
            if(["fr","en","de","es"].indexOf(language)>=0) return language;
         }
         if(param1 == "lang" && this._flashVars.getItem(param1) == null) return "en";
         return this._flashVars.getItem(param1);
      }
   }
}

