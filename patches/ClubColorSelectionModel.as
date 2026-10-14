package com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.model
{
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.event.ClubColorSelectionEvent;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.ClubPaletteItem;
   import com.ankamagames.xgaming.utils.collections.Collections;
   import com.ankamagames.xgaming.utils.display.Color3;
   import org.robotlegs.mvcs.Actor;
   
   public class ClubColorSelectionModel extends Actor
   {
      
      public static const SELECTABLE_COLORS_UPDATED:String = "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.model.ClubColorSelectionModel.SELECTABLE_COLORS_UPDATED";
      
      public static const SELECTED_COLORS_UPDATED:String = "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.model.ClubColorSelectionModel.SELECTED_COLORS_UPDATED";
      
      private var _currentPalette:ClubPaletteItem;
      
      private var _mainColorIsDark:Boolean;
      
      private var _mainColorId:uint;
      
      private var _alternateColorId:uint;
      
      private var _sigilColorId:uint;
      
      public function ClubColorSelectionModel()
      {
         super();
         this._mainColorIsDark = true;
      }
      
      public function get darkColors() : Array
      {
         return this._currentPalette.darkColors;
      }
      
      public function get lightColors() : Array
      {
         return this._currentPalette.lightColors;
      }
      
      public function get alternateColors() : Array
      {
         return this.mainColorIsDark ? this.lightColors : this.darkColors;
      }
      
      public function get sigilColors() : Array
      {
         return this._currentPalette.sigilColors;
      }
      
      public function get mainColorIsDark() : Boolean
      {
         return this._mainColorIsDark;
      }
      
      public function get mainColorId() : uint
      {
         return this._mainColorId;
      }
      
      public function get alternateColorId() : uint
      {
         return this._alternateColorId;
      }
      
      public function set alternateColorId(param1:uint) : void
      {
         this._alternateColorId = this.validIndex(param1,this.alternateColors);
         this.updateSelectableColors();
         this.updateSelectedColors();
      }
      
      public function get sigilColorId() : uint
      {
         return this._sigilColorId;
      }
      
      public function set sigilColorId(param1:uint) : void
      {
         this._sigilColorId = this.validIndex(param1,this.sigilColors);
         this.updateSelectableColors();
         this.updateSelectedColors();
      }
      
      public function get paletteId() : int
      {
         return this._currentPalette.id;
      }
      
      public function get mainColor() : Color3
      {
         return this.mainColorIsDark ? this.darkColors[this._mainColorId] : this.lightColors[this._mainColorId];
      }
      
      public function set mainColor(param1:Color3) : void
      {
         var _loc2_:int = Collections.arrayIndexOf(this.darkColors,param1);
         if(_loc2_ != -1)
         {
            this.setMainColor(0,_loc2_);
            return;
         }
         _loc2_ = Collections.arrayIndexOf(this.lightColors,param1);
         if(_loc2_ != -1)
         {
            this.setMainColor(1,_loc2_);
            return;
         }
         this._mainColorIsDark = true;
         this._mainColorId = 0;
      }
      
      public function get alternateColor() : Color3
      {
         return this.alternateColors[this._alternateColorId];
      }
      
      public function set alternateColor(param1:Color3) : void
      {
         var _loc2_:int = Collections.arrayIndexOf(this.alternateColors,param1);
         this.alternateColorId = _loc2_ == -1 ? 0 : uint(_loc2_);
      }
      
      public function get sigilColor() : Color3
      {
         return this.sigilColors[this._sigilColorId];
      }
      
      public function set sigilColor(param1:Color3) : void
      {
         var _loc2_:int = Collections.arrayIndexOf(this.sigilColors,param1);
         this.sigilColorId = _loc2_ == -1 ? 0 : uint(_loc2_);
      }
      
      public function set currentPalette(param1:ClubPaletteItem) : void
      {
         if(param1 == null) return;
         this._currentPalette = param1;
         this._mainColorId = this.validIndex(this._mainColorId,this.mainColorIsDark ? this.darkColors : this.lightColors);
         this._alternateColorId = this.validIndex(this._alternateColorId,this.alternateColors);
         this._sigilColorId = this.validIndex(this._sigilColorId,this.sigilColors);
         this.updateSelectableColors();
         this.updateSelectedColors();
      }
      
      public function setMainColor(param1:uint, param2:uint) : void
      {
         this._mainColorIsDark = param1 == 0;
         this._mainColorId = this.validIndex(param2,this.mainColorIsDark ? this.darkColors : this.lightColors);
         this._alternateColorId = this.validIndex(this._alternateColorId,this.alternateColors);
         this.updateSelectableColors();
         this.updateSelectedColors();
      }
      
      private function validIndex(index:uint, colors:Array) : uint
      {
         return colors != null && index < colors.length ? index : 0;
      }
      private function updateSelectableColors() : void
      {
         dispatch(new ClubColorSelectionEvent(SELECTABLE_COLORS_UPDATED,this));
      }
      
      private function updateSelectedColors() : void
      {
         dispatch(new ClubColorSelectionEvent(SELECTED_COLORS_UPDATED,this));
      }
   }
}

