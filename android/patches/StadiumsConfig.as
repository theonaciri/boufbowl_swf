package com.ankamagames.boufbowl.client.application
{
   import as3.collections.IArrayList;
   import as3.collections.IMap;
   import as3.collections.Map;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.config.IStadiumsConfig;
   import com.ankamagames.boufbowl.config.StadiumSpecificData;
   import com.ankamagames.boufbowl.protocol.Stadium;
   import com.ankamagames.xgaming.utils.collections.Collections;
   import com.ankamagames.xgaming.utils.config.JSONConfig;
   import com.ankamagames.xgaming.utils.inspection.IEnumConverter;
   import com.ankamagames.xgaming.utils.inspection.enumConverterFor;
   
   public class StadiumsConfig extends JSONConfig implements IStadiumsConfig
   {
      
      private var _stadiumsPath:String;
      
      private var _stadiumData:IMap = new Map();
      
      public function StadiumsConfig(param1:String)
      {
         super(param1);
      }
      
      public function get stadiums() : IArrayList
      {
         return Collections.arrayToList(this._stadiumData.keysToArray());
      }
      
      public function getStadiumData(param1:int) : StadiumSpecificData
      {
         return this._stadiumData.getItem(param1);
      }
      
      override protected function decoded(param1:Object) : void
      {
         var _loc4_:int = 0;
         this._stadiumsPath = getString(param1,["stadiumsPath"],"app:/assets/models/stadiums/");
         var _loc2_:IEnumConverter = enumConverterFor(Stadium);
         var _loc3_:IIterator = _loc2_.values.getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            this._stadiumData.addItem(_loc4_,this.buildStadiumData(_loc2_.toString(_loc4_),param1));
         }
      }
      
      private function buildStadiumData(param1:String, param2:Object) : StadiumSpecificData
      {
         var _loc3_:String = this._stadiumsPath + getString(param2,["stadiums",param1,"path"],"error");
         var _loc4_:uint = uint(getInt(param2,["stadiums",param1,"cellStrokeColor"],3355443));
         var _loc5_:Number = getNumber(param2,["stadiums",param1,"cellStrokeAlpha"],0.1);
         var _loc6_:uint = uint(getInt(param2,["stadiums",param1,"centerPlacementZoneColor"],16711680));
         var _loc7_:Number = getNumber(param2,["stadiums",param1,"centerPlacementZoneAlpha"],0.25);
         var _loc8_:uint = uint(getInt(param2,["stadiums",param1,"frontRightPlacementZoneColor"],65280));
         var _loc9_:Number = getNumber(param2,["stadiums",param1,"frontRightPlacementZoneAlpha"],0.25);
         var _loc10_:uint = uint(getInt(param2,["stadiums",param1,"frontLeftPlacementZoneColor"],255));
         var _loc11_:Number = getNumber(param2,["stadiums",param1,"frontLeftPlacementZoneAlpha"],0.25);
         var _loc12_:uint = uint(getInt(param2,["stadiums",param1,"backRightPlacementZoneColor"],16776960));
         var _loc13_:Number = getNumber(param2,["stadiums",param1,"backRightPlacementZoneAlpha"],0.25);
         var _loc14_:uint = uint(getInt(param2,["stadiums",param1,"backLeftPlacementZoneColor"],65535));
         var _loc15_:Number = getNumber(param2,["stadiums",param1,"backLeftPlacementZoneAlpha"],0.25);
         var _loc16_:uint = uint(getInt(param2,["stadiums",param1,"riskyZoneStartColor"],15619328));
         var _loc17_:Number = getNumber(param2,["stadiums",param1,"riskyZoneStartAlpha"],0.1);
         var _loc18_:uint = uint(getInt(param2,["stadiums",param1,"riskyZoneEndColor"],16711680));
         var _loc19_:Number = getNumber(param2,["stadiums",param1,"riskyZoneEndAlpha"],0.25);
         var _loc20_:uint = uint(getInt(param2,["stadiums",param1,"forbiddenZoneColor"],3280433));
         var _loc21_:Number = getNumber(param2,["stadiums",param1,"forbiddenZoneAlpha"],0.2);
         var _loc22_:uint = uint(getInt(param2,["stadiums",param1,"safeZoneColor"],0));
         var _loc23_:Number = getNumber(param2,["stadiums",param1,"safeZoneAlpha"],0);
         var _loc24_:IArrayList = getStringArray(param2,["stadiums",param1,"strategicMusics"],Collections.list());
         var _loc25_:IArrayList = getStringArray(param2,["stadiums",param1,"resolutionMusics"],Collections.list());
         var _loc26_:String = getString(param2,["stadiums",param1,"introScriptClass"],"");
         var _loc27_:String = getString(param2,["stadiums",param1,"ambiantTrackName"],"");
         var _loc28_:String = getString(param2,["stadiums",param1,"reboundCutsceneName"],"");
         var _loc29_:String = getString(param2,["stadiums",param1,"publicHappyCutsceneName"],"");
         var _loc30_:Boolean = getBoolean(param2,["stadiums",param1,"hasPublic"],false);
         var _loc31_:String = getString(param2,["stadiums",param1,"publicHappySound"],"");
         return new StadiumSpecificData(_loc3_,_loc4_,_loc5_,_loc6_,_loc7_,_loc8_,_loc9_,_loc10_,_loc11_,_loc12_,_loc13_,_loc14_,_loc15_,_loc16_,_loc17_,_loc18_,_loc19_,_loc20_,_loc21_,_loc22_,_loc23_,_loc24_,_loc25_,_loc26_,_loc27_,_loc28_,_loc29_,_loc30_,_loc31_);
      }
   }
}

