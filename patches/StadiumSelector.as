package com.ankamagames.boufbowl.ui.components.matchcreation.stadium
{
   import as3.collections.IMap;
   import as3.collections.iterators.IMapIterator;
   import com.ankamagames.xgaming.ui.components.FlashInstanceContainer;
   import com.ankamagames.xgaming.utils.event.IndexEvent;
   import flash.events.MouseEvent;
   
   public class StadiumSelector extends FlashInstanceContainer
   {
      
      public static const STADIUM_ROLLED_OVER:String = "com.ankamagames.boufbowl.ui.components.matchcreation.StadiumSelector.STADIUM_ROLLED_OVER";
      
      public static const STADIUM_CLICKED:String = "com.ankamagames.boufbowl.ui.components.matchcreation.StadiumSelector.STADIUM_CLICKED";
      
      private var _stadiumsSpritesAmount:int = 12;
      
      private var _stadiums:IMap;
      
      private var _selectedStadiumId:int;
      
      private var _selectableStadiums:Boolean = true;
      
      public function StadiumSelector()
      {
         super();
      }
      
      public function set selectableStadiums(param1:Boolean) : void
      {
         this._selectableStadiums = param1;
      }
      
      public function get selectedStadium() : int
      {
         return this._selectedStadiumId;
      }
      
      public function set selectedStadium(param1:int) : void
      {
         this.selectStadium(param1);
      }
      
      public function setup(param1:IMap) : void
      {
         this._stadiums = param1;
         this.updateStadiumsList();
      }
      
      public function getStadium(param1:int) : StadiumPreviewWithAvailability
      {
         if(param1 < 0 || this._stadiumsSpritesAmount < param1)
         {
            throw new RangeError("Stadium index must be a number between 0 and " + (this._stadiumsSpritesAmount - 1) + " !");
         }
         return getFlashInstance("miniStadiumSprite_" + param1,StadiumPreviewWithAvailability);
      }
      
      override protected function initFlashInstances() : void
      {
         super.initFlashInstances();
         var _loc1_:int = 0;
         while(_loc1_ < this._stadiumsSpritesAmount)
         {
            getFlashInstance("miniStadiumSprite_" + _loc1_,StadiumPreviewWithAvailability);
            _loc1_++;
         }
      }
      
      private function updateStadiumsList() : void
      {
         var _loc3_:StadiumViewData = null;
         var _loc1_:IMapIterator = this._stadiums.getMapIterator();
         var _loc2_:int = 0;
         while(_loc1_.hasNext())
         {
            _loc3_ = _loc1_.getNext();
            this.getStadium(_loc2_).visible = true;
            this.getStadium(_loc2_).update(_loc1_.getKey(),_loc3_.availability);
            this.getStadium(_loc2_).addEventListener(MouseEvent.ROLL_OVER,this.stadiumRollOverHandler);
            this.getStadium(_loc2_).addEventListener(MouseEvent.CLICK,this.stadiumClickHandler);
            _loc2_++;
         }
         if(_loc2_ < this._stadiumsSpritesAmount)
         {
            while(_loc2_ < this._stadiumsSpritesAmount)
            {
               this.getStadium(_loc2_).visible = false;
               this.getStadium(_loc2_).removeEventListener(MouseEvent.ROLL_OVER,this.stadiumRollOverHandler);
               this.getStadium(_loc2_).removeEventListener(MouseEvent.CLICK,this.stadiumClickHandler);
               _loc2_++;
            }
         }
      }
      
      private function stadiumRollOverHandler(event:MouseEvent) : void
      {
         var preview:StadiumPreviewWithAvailability=StadiumPreviewWithAvailability(event.currentTarget);
         dispatchEvent(new IndexEvent(STADIUM_ROLLED_OVER,preview.stadiumId));
      }

      private function stadiumClickHandler(event:MouseEvent) : void
      {
         var preview:StadiumPreviewWithAvailability=StadiumPreviewWithAvailability(event.currentTarget);
         if(!this._selectableStadiums) { preview.selected=false;return; }
         this.selectStadium(preview.stadiumId);
         dispatchEvent(new IndexEvent(STADIUM_CLICKED,preview.stadiumId));
      }

      private function selectStadium(param1:int) : void
      {
         var _loc3_:StadiumPreviewWithAvailability = null;
         var _loc2_:int = 0;
         while(_loc2_ < this._stadiumsSpritesAmount)
         {
            _loc3_ = getFlashInstance("miniStadiumSprite_" + _loc2_,StadiumPreviewWithAvailability);
            _loc3_.selected = _loc3_.stadiumId == param1;
            _loc2_++;
         }
         this._selectedStadiumId = param1;
      }
   }
}

