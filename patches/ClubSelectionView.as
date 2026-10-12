package com.ankamagames.boufbowl.client.clubselection.view
{
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   import as3.collections.ArrayList;
   import as3.collections.ILinkedMap;
   import as3.collections.IList;
   import as3.collections.IMap;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.club.view.ClubIllustrationView;
   import com.ankamagames.boufbowl.client.club.view.IllustrationViewFactory;
   import com.ankamagames.boufbowl.client.clubselection.event.ColorSelectedEvent;
   import com.ankamagames.boufbowl.client.components.blason.BlasonIconUI;
   import com.ankamagames.boufbowl.client.components.clubedition.ClubEditorUI;
   import com.ankamagames.boufbowl.client.components.clubselection.ColorGrid;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.strategic.model.RulesConstants;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.SigilBackgroundItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.SigilChargeItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.view.PaletteLineFactory;
   import com.ankamagames.boufbowl.protocol.Role;
   import com.ankamagames.boufbowl.ui.components.blason.BlasonAvailabilityUI;
   import com.ankamagames.boufbowl.ui.components.blason.BlasonBackgroundUI;
   import com.ankamagames.boufbowl.ui.components.clubedition.OpenBlasonSelectorButton;
   import com.ankamagames.boufbowl.ui.components.color.ColorGridEvent;
   import com.ankamagames.xgaming.ui.components.list.ItemSelectorList;
   import com.ankamagames.xgaming.ui.event.ItemSelectedEvent;
   import com.ankamagames.xgaming.utils.collections.Collections;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.event.IndexEvent;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.ui.TextFieldColor;
   import com.netease.protobuf.UInt64;
   import flash.events.FocusEvent;
   import flash.events.MouseEvent;
   
   public class ClubSelectionView extends ClubEditorUI
   {
      
      public static const SELECTED_GRID_CHANGED:String = "com.ankamagames.boufbowl.client.clubselection.view.ClubSelectionView.SELECTED_GRID_CHANGED";
      
      public static const SELECTED_PALETTE_CHANGED:String = "com.ankamagames.boufbowl.client.clubselection.view.ClubSelectionView.SELECTED_PALETTE_CHANGED";
      
      public static const SELECTED_COLOR_CHANGED:String = "com.ankamagames.boufbowl.client.clubselection.view.ClubSelectionView.SELECTED_COLOR_CHANGED";
      
      public static const SELECTED_SIGIL_CHARGE_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.view.ClubEditorView.SELECTED_SIGIL_CHARGE_CHANGED";
      
      public static const SELECTED_SIGIL_BACKGROUND_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.view.ClubEditorView.SELECTED_SIGIL_BACKGROUND_CHANGED";
      
      private var _maxBoufbowlerCountPerRole:int;
      
      private var _clubIllustration:ClubIllustrationView;
      
      private var _predefinedClubName:String;
      
      private var _paletteLineBuilder:PaletteLineFactory;
      
      private var _translator:ITranslator;
      
      private var _clubNameColorField:TextFieldColor;
      
      public function ClubSelectionView(param1:RulesConstants, param2:IllustrationViewFactory, param3:PaletteLineFactory, param4:ITranslator)
      {
         super();
         this._maxBoufbowlerCountPerRole = param1.maxBoufbowlerCountPerRole;
         this._clubIllustration = param2.getClubIllustration();
         this._paletteLineBuilder = param3;
         this._translator = param4;
         this.init();
      }
      
      public function updateClubInfos(param1:UInt64) : void
      {
         var _loc2_:String = param1 == null ? "" : StartUpApplicationCommand.teamName(param1);
         if(teamName == this._predefinedClubName || teamName.length == 0)
         {
            teamName = _loc2_;
         }
         this._predefinedClubName = _loc2_;
         this.updateClubNameTextColor();
         if(param1 != null)
         {
            teamDescription = "Local sample team. Customize its name, colors and emblem.";
         }
      }
      
      public function updateRolesCount(param1:IMap) : void
      {
         throwerCount = this.buildRoleCountText(param1,Role.THROWER);
         dodgerCount = this.buildRoleCountText(param1,Role.DODGER);
         runnerCount = this.buildRoleCountText(param1,Role.RUNNER);
         blockerCount = this.buildRoleCountText(param1,Role.BLOCKER);
      }
      
      public function updateTeamIndicator(param1:int, param2:int) : void
      {
         teamIndicator = this._translator.getText(LangConstants.CLUBSELECTION_TEAM_INDICATOR,param1,param2);
      }
      
      public function updateIllustration(param1:Array) : void
      {
         if(param1 == null)
         {
            explainTextField.visible = true;
            this._clubIllustration.visible = false;
         }
         else
         {
            explainTextField.visible = false;
            this._clubIllustration.visible = true;
            this._clubIllustration.update(param1);
         }
      }
      
      internal function updateSelectableColors(param1:Array, param2:Array, param3:Array, param4:Array) : void
      {
         colorGrid_1.update(param1,param2);
         colorGrid_2.update(param3);
         colorGrid_3.update(param4);
      }
      
      internal function updateSelectedColors(param1:Boolean, param2:uint, param3:uint, param4:uint, param5:Color3, param6:Color3, param7:Color3) : void
      {
         colorGrid1.selectColorId(param1 ? 0 : 1,param2);
         colorGrid2.selectColorId(0,param3);
         colorGrid3.selectColorId(0,param4);
         blason.updateColors(param5,param6,param7);
      }
      
      internal function setAvailablePalettes(param1:ILinkedMap) : void
      {
         paletteSelector.setListItems(this._paletteLineBuilder.createClubPaletteLines(Collections.iteratorToList(param1.getIterator())));
      }
      
      internal function setAvailableSigils(param1:ILinkedMap, param2:ILinkedMap) : void
      {
         var _loc4_:SigilChargeItem = null;
         var _loc5_:BlasonAvailabilityUI = null;
         var _loc6_:BlasonIconUI = null;
         var _loc8_:SigilBackgroundItem = null;
         var _loc9_:BlasonBackgroundUI = null;
         var _loc10_:IList = null;
         var _loc3_:IIterator = param2.getIterator();
         var _loc7_:IList = new ArrayList();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            _loc6_ = new BlasonIconUI();
            _loc6_.setIconType(_loc4_.charge);
            _loc5_ = new BlasonAvailabilityUI();
            _loc5_.buttonMode = true;
            _loc5_.update(_loc6_,_loc4_.availability,_loc4_.charge);
            _loc7_.addItem(_loc5_);
         }
         OpenBlasonSelectorButton(sigilChargeSelector.openButton).icon = OpenBlasonSelectorButton.CHARGE;
         sigilChargeSelector.setListItems(_loc7_);
         _loc3_ = param1.getIterator();
         _loc10_ = new ArrayList();
         while(_loc3_.hasNext())
         {
            _loc8_ = _loc3_.getNext();
            _loc9_ = new BlasonBackgroundUI();
            _loc9_.setBackgroundType(_loc8_.background);
            _loc5_ = new BlasonAvailabilityUI();
            _loc5_.buttonMode = true;
            _loc5_.update(_loc9_,_loc8_.availability,_loc8_.background);
            _loc10_.addItem(_loc5_);
         }
         OpenBlasonSelectorButton(sigilBackgroundSelector.openButton).icon = OpenBlasonSelectorButton.BACKGROUND;
         sigilBackgroundSelector.setListItems(_loc10_);
      }
      
      internal function updateBlazon(param1:int, param2:int) : void
      {
         blason.update(param2,param1);
      }
      
      private function buildRoleCountText(param1:IMap, param2:int) : String
      {
         var _loc3_:int = param1.getItem(param2);
         var _loc4_:String = "";
         if(_loc3_ > this._maxBoufbowlerCountPerRole)
         {
            _loc4_ += "<font color=\"#ff0000\">";
         }
         _loc4_ += this._translator.getEnumTranslation(LangConstants.PREMIUMSERVICE_ROLE_COUNT_ENUM,param2,_loc3_,this._maxBoufbowlerCountPerRole);
         if(_loc3_ > this._maxBoufbowlerCountPerRole)
         {
            _loc4_ += "</font>";
         }
         return _loc4_;
      }
      
      private function paletteSelectorLineSelectedHandler(param1:ItemSelectedEvent) : void
      {
         param1.preventDefault();
         dispatchEvent(new IndexEvent(SELECTED_PALETTE_CHANGED,param1.item.id));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.CUSTOMIZATION_PALETTESELECTOR_CLOSED));
      }
      
      private function init() : void
      {
         title = this._translator.getText(LangConstants.CLUBSELECTION_TITLE);
         teamLabel = this._translator.getText(LangConstants.CLUBSELECTION_TEAMNAME_LABEL);
         explainTextField.htmlText = this._translator.getText(LangConstants.CLUBSELECTION_EXPLANATION);
         explainBottomField.visible = false;
         illustrationHolder.scaleX = illustrationHolder.scaleY = 0.9;
         illustrationHolder.addChild(this._clubIllustration);
         this._clubNameColorField = new TextFieldColor(clubNameField,16777215,16777215,0);
         clubNameField.addEventListener(FocusEvent.FOCUS_IN,this.clubNameFieldFocusHandler,false,0,true);
         clubNameField.addEventListener(FocusEvent.FOCUS_OUT,this.clubNameFieldFocusHandler,false,0,true);
         refreshButton.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_REFRESH_BUTTON_TOOLTIP));
         validateButton.componentLabel = this._translator.getText(LangConstants.OK);
         colorGrid1.addEventListener(ColorGridEvent.CHANGE,this.colorGridCellClickHandler);
         colorGrid2.addEventListener(ColorGridEvent.CHANGE,this.colorGridCellClickHandler);
         colorGrid3.addEventListener(ColorGridEvent.CHANGE,this.colorGridCellClickHandler);
         paletteSelector.list.title = this._translator.getText(LangConstants.PALETTE_SELECTOR_TITLE);
         paletteSelector.setTooltip(this._translator.getText(LangConstants.PALETTE_SELECTOR_TOOLTIP));
         paletteSelector.list.addEventListener(ItemSelectorList.ITEM_SELECTED,this.paletteSelectorLineSelectedHandler);
         paletteSelector.openButton.addEventListener(MouseEvent.CLICK,this.itemSelectorClicked);
         sigilBackgroundSelector.openButton.addEventListener(MouseEvent.CLICK,this.itemSelectorClicked);
         sigilChargeSelector.openButton.addEventListener(MouseEvent.CLICK,this.itemSelectorClicked);
         sigilChargeSelector.list.title = this._translator.getText(LangConstants.PREMIUMSERVICE_SIGILCHARGE_SELECTOR_TITLE);
         sigilChargeSelector.list.addEventListener(ItemSelectorList.ITEM_SELECTED,this.sigilChargeSelectedHandler,false,0,true);
         sigilChargeSelector.setTooltip(this._translator.getText(LangConstants.PREMIUMSERVICE_OPEN_SIGILCHARGE_SELECTOR_TOOLTIP));
         sigilBackgroundSelector.list.title = this._translator.getText(LangConstants.PREMIUMSERVICE_SIGILBACKGROUND_SELECTOR_TITLE);
         sigilBackgroundSelector.list.addEventListener(ItemSelectorList.ITEM_SELECTED,this.sigilBackgroundSelectedHandler,false,0,true);
         sigilBackgroundSelector.setTooltip(this._translator.getText(LangConstants.PREMIUMSERVICE_OPEN_SIGILBACKGROUND_SELECTOR_TOOLTIP));
      }
      
      private function itemSelectorClicked(param1:MouseEvent) : void
      {
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.CUSTOMIZATION_PALETTESELECTOR_OPEN));
      }
      
      private function sigilChargeSelectedHandler(param1:ItemSelectedEvent) : void
      {
         dispatchEvent(new IndexEvent(SELECTED_SIGIL_CHARGE_CHANGED,param1.item.id));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.TEAMCUSTOMIZATION_SIGILSELECTOR_CLOSED));
      }
      
      private function sigilBackgroundSelectedHandler(param1:ItemSelectedEvent) : void
      {
         dispatchEvent(new IndexEvent(SELECTED_SIGIL_BACKGROUND_CHANGED,param1.item.id));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.TEAMCUSTOMIZATION_SIGILSELECTOR_CLOSED));
      }
      
      private function clubNameFieldFocusHandler(param1:FocusEvent) : void
      {
         switch(param1.type)
         {
            case FocusEvent.FOCUS_IN:
               if(clubNameField.text == this._predefinedClubName)
               {
                  clubNameField.text = "";
               }
               break;
            case FocusEvent.FOCUS_OUT:
               if(clubNameField.text.length == 0)
               {
                  clubNameField.text = this._predefinedClubName;
               }
         }
         this.updateClubNameTextColor();
      }
      
      private function updateClubNameTextColor() : void
      {
         this._clubNameColorField.textColor = clubNameField.text == this._predefinedClubName ? 8947848 : 16777215;
      }
      
      private function colorGridCellClickHandler(param1:ColorGridEvent) : void
      {
         var _loc2_:int = parseInt(ColorGrid(param1.currentTarget).name.substring(10),10) - 1;
         dispatchEvent(new ColorSelectedEvent(SELECTED_COLOR_CHANGED,_loc2_,param1.lineIndex,param1.cellLineIndex));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.CUSTOMIZATION_COLOR_CHOSEN));
      }
   }
}

