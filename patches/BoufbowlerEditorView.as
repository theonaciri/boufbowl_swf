package com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view
{
   import as3.collections.ILinkedMap;
   import as3.collections.IMap;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.application.IColorScheme;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.boufbowler.BoufbowlerTooltipBuilder;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.club.view.BoufbowlerIllustrationView;
   import com.ankamagames.boufbowl.client.club.view.BoufbowlerPosingType;
   import com.ankamagames.boufbowl.client.club.view.ClubIllustrationView;
   import com.ankamagames.boufbowl.client.club.view.IllustrationViewFactory;
   import com.ankamagames.boufbowl.client.clubselection.event.ColorSelectedEvent;
   import com.ankamagames.boufbowl.client.components.clubedition.BoufbowlerEditorUI;
   import com.ankamagames.boufbowl.client.components.clubedition.ClassSelectorUI;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.strategic.model.BoufbowlerAttributesModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IClubBoufbowlerModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.RulesConstants;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.BoufbowlerPaletteItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.view.PaletteLineFactory;
   import com.ankamagames.boufbowl.protocol.RegularOrderData.Element;
   import com.ankamagames.boufbowl.protocol.Role;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;
   import com.ankamagames.boufbowl.ui.components.attributes.AttributeTag;
   import com.ankamagames.boufbowl.ui.components.clubedition.BoufbowlerPictures;
   import com.ankamagames.boufbowl.ui.components.clubedition.ClassPedestal;
   import com.ankamagames.boufbowl.ui.components.clubedition.EditorLabelIcon;
   import com.ankamagames.boufbowl.ui.components.color.ColorGridEvent;
   import com.ankamagames.xgaming.ui.components.list.ItemSelectorList;
   import com.ankamagames.xgaming.ui.event.ItemSelectedEvent;
   import com.ankamagames.xgaming.utils.collections.Collections;
   import com.ankamagames.xgaming.utils.event.IndexEvent;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.events.Event;
   import flash.events.FocusEvent;
   import flash.events.MouseEvent;
   import flash.events.TextEvent;
   
   public class BoufbowlerEditorView extends BoufbowlerEditorUI
   {
      
      public static const NAME_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.view.boufbowler.BoufbowlerEditorView.NAME_CHANGED";
      
      public static const CANCEL_CLICKED:String = "com.ankamagames.boufbowl.client.premiumservice.view.boufbowler.BoufbowlerEditorView.CANCEL_CLICKED";
      
      public static const SELECTED_PALETTE_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view.BoufbowlerEditorView.SELECTED_PALETTE_CHANGED";
      
      public static const SELECTED_COLOR_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view.BoufbowlerEditorView.SELECTED_COLOR_CHANGED";
      
      public static const CLASS_SELECTED:String = "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view.BoufbowlerEditorView.CLASS_SELECTED";
      
      public static const SKIN_SELECTED:String = "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view.BoufbowlerEditorView.SKIN_SELECTED";
      
      private var _tooltipBuilder:BoufbowlerTooltipBuilder;
      
      private var _classSelector:ClassSelectorUI;
      
      private var _boufbowlerIllustration:BoufbowlerIllustrationView;
      
      private var _clubIllustration:ClubIllustrationView;
      
      private var _boufbowlerSpriteHolder:BoufbowlerEditorSpriteHolderView;
      
      private var _colorScheme:IColorScheme;
      
      private var _translator:ITranslator;
      
      private var _illustrationViewFactory:IllustrationViewFactory;
      
      private var _maxBoufbowlerCountPerRole:int;
      
      private var _paletteLineBuilder:PaletteLineFactory;
      
      public function BoufbowlerEditorView(param1:BoufbowlerEditorSpriteHolderView, param2:ClassSelectorUI, param3:IColorScheme, param4:ITranslator, param5:IllustrationViewFactory, param6:RulesConstants, param7:BoufbowlerTooltipBuilder, param8:PaletteLineFactory)
      {
         super();
         this._boufbowlerIllustration = param5.getBoufbowlerIllustration(BoufbowlerPosingType.DEFAULT);
         this._clubIllustration = param5.getClubIllustration();
         this._boufbowlerSpriteHolder = param1;
         this._classSelector = param2;
         this._colorScheme = param3;
         this._translator = param4;
         this._illustrationViewFactory = param5;
         this._maxBoufbowlerCountPerRole = param6.maxBoufbowlerCountPerRole;
         this._tooltipBuilder = param7;
         this._paletteLineBuilder = param8;
         this.initUI();
         this.initTexts();
      }
      
      internal function updateName(param1:IClubBoufbowlerModel, param2:ClubModel) : void
      {
         boufbowlerName.text = param1.name;
         this._boufbowlerIllustration.update(param1);
         this._clubIllustration.update(param2.boufbowlers.toArray());
         this._clubIllustration.highlightBoufbowler(param1.id);
      }
      
      internal function updateAttributes(param1:IClubBoufbowlerModel, param2:ClubModel) : void
      {
         prevFieldPostureButton.visible = nextFieldPostureButton.visible = true;
         this._classSelector.setSelectedPicture(param1.skinId);
         actualClassIndicator.updateSkin(param1.skinId);
         this.updateClassOrderInfos(param1.boufbowlerClass);
         this.updateRolesCount(param2.getBoufbowlerCountByRole());
         this.updateGauges(param1);
         this._boufbowlerIllustration.update(param1);
         this._clubIllustration.update(param2.boufbowlers.toArray());
         this._clubIllustration.highlightBoufbowler(param1.id);
         this._boufbowlerSpriteHolder.updateBoufbowler(param1);
      }
      
      internal function updateColors(param1:int, param2:int, param3:int, param4:IClubBoufbowlerModel, param5:ClubModel) : void
      {
         hairColorGrid.selectColorId(0,param1);
         skinColorGrid.selectColorId(0,param2);
         eyesColorGrid.selectColorId(0,param3);
         this._boufbowlerIllustration.update(param4);
         this._clubIllustration.update(param5.boufbowlers.toArray());
         this._clubIllustration.highlightBoufbowler(param4.id);
         this._boufbowlerSpriteHolder.updateBoufbowler(param4);
      }
      
      internal function updateAnimation(param1:AnimationKey, param2:IClubBoufbowlerModel) : void
      {
         prevFieldPostureButton.visible = nextFieldPostureButton.visible = true;
         this._boufbowlerSpriteHolder.currentAnimationKey = param1;
         this._boufbowlerSpriteHolder.updateAnimation(param2);
      }
      
      internal function setApplicablePalettes(param1:ILinkedMap) : void
      {
         paletteSelector.setListItems(this._paletteLineBuilder.createBoufbowlerPaletteLines(Collections.iteratorToList(param1.getIterator())));
      }
      
      internal function updatePalette(param1:BoufbowlerPaletteItem) : void
      {
         eyesColorGrid.update(param1.eyeColors);
         hairColorGrid.update(param1.hairColors);
         skinColorGrid.update(param1.skinColors);
      }
      
      internal function initClassSelectorTooltips(param1:IMap) : void
      {
         var _loc3_:int = 0;
         var _loc4_:IClubBoufbowlerModel = null;
         var _loc2_:IIterator = param1.getIterator();
         while(_loc2_.hasNext())
         {
            _loc4_ = _loc2_.getNext();
            this._classSelector.setClassIconTooltip(_loc4_.boufbowlerClass,this._translator.getEnumTranslation(LangConstants.CLASSES_DESC,_loc4_.boufbowlerClass) + BoufbowlerTooltipBuilder.NEW_LINE + BoufbowlerTooltipBuilder.NEW_LINE + this._tooltipBuilder.buildBoufbowlerClassTooltip(_loc4_));
         }
         this.initClassSelectorRolesTooltips(Role.BLOCKER);
         this.initClassSelectorRolesTooltips(Role.DODGER);
         this.initClassSelectorRolesTooltips(Role.RUNNER);
         this.initClassSelectorRolesTooltips(Role.THROWER);
      }
      
      internal function updateBoufbowlerSelector(param1:IMap, param2:Array, param3:Boolean, param4:IClubBoufbowlerModel, param5:int) : void
      {
         var _loc7_:IClubBoufbowlerModel = null;
         var _loc8_:Boolean = false;
         var _loc9_:Boolean = false;
         this._classSelector.clearPictures();
         var _loc6_:IIterator = param1.getIterator();
         while(_loc6_.hasNext())
         {
            _loc7_ = _loc6_.getNext();
            _loc8_ = param3 || _loc7_.boufbowlerClass == param5;
            _loc9_ = !_loc7_.isUniqueCharacter || (param2.indexOf(_loc7_.uniqueCharacter) == -1 || Boolean(param4.isUniqueCharacter) && param4.uniqueCharacter == _loc7_.uniqueCharacter);
            if(!param3) _loc9_ = _loc9_ && _loc7_.isUniqueCharacter == param4.isUniqueCharacter && (!_loc7_.isUniqueCharacter || _loc7_.uniqueCharacter == param4.uniqueCharacter);
            if(_loc7_.boufbowlerClass == param5)
            {
               this.updatePictures(_loc7_,_loc9_,_loc7_.availability);
            }
            this._classSelector.setClassIconEnabled(_loc7_.boufbowlerClass,_loc8_);
         }
         this._classSelector.setSelectedPicture(param4.skinId);
         this._classSelector.setSelectedClass(param5);
      }
      
      private function initClassSelectorRolesTooltips(param1:int) : void
      {
         this._classSelector.setRoleTooltip(param1,this._translator.getEnumTranslation(LangConstants.ROLES_DESC,param1));
      }
      
      private function updatePictures(param1:IClubBoufbowlerModel, param2:Boolean, param3:int) : void
      {
         var _loc4_:BoufbowlerIllustrationView = this._illustrationViewFactory.getBoufbowlerIllustration(BoufbowlerPosingType.DEFAULT,false);
         _loc4_.update(param1);
         _loc4_.x = 0;
         _loc4_.y = 240;
         this._classSelector.setPicture(_loc4_,param1.gender,param1.isUniqueCharacter,param2,param3,param1.role,param1.skinId,this._tooltipBuilder.buildCompleteBoufbowlerTooltip(param1));
      }
      
      private function updateRolesCount(param1:IMap) : void
      {
         throwerCount = this.buildRoleCountText(param1,Role.THROWER);
         dodgerCount = this.buildRoleCountText(param1,Role.DODGER);
         runnerCount = this.buildRoleCountText(param1,Role.RUNNER);
         blockerCount = this.buildRoleCountText(param1,Role.BLOCKER);
      }
      
      private function buildRoleCountText(param1:IMap, param2:int) : String
      {
         var _loc3_:int = param1.getItem(param2);
         var _loc4_:String = "";
         if(_loc3_ > this._maxBoufbowlerCountPerRole)
         {
            _loc4_ += "<font color=\"#ff0000\">";
         }
         _loc4_ += this._translator.getText(LangConstants.PREMIUMSERVICE_ROLE_COUNT_SHORT,_loc3_,this._maxBoufbowlerCountPerRole);
         if(_loc3_ > this._maxBoufbowlerCountPerRole)
         {
            _loc4_ += "</font>";
         }
         return _loc4_;
      }
      
      private function initUI() : void
      {
         skinLabelIcon.icon = EditorLabelIcon.LOOK_SKIN;
         hairLabelIcon.icon = EditorLabelIcon.LOOK_HAIRS;
         eyesLabelIcon.icon = EditorLabelIcon.LOOK_EYES;
         this._boufbowlerIllustration.scaleX = this._boufbowlerIllustration.scaleY = 1.6;
         boufbowlerHolder.addChild(this._boufbowlerIllustration);
         this._clubIllustration.scaleX = this._clubIllustration.scaleY = 0.44;
         teamCutsceneHolder.addChild(this._clubIllustration);
         this._boufbowlerSpriteHolder.scaleX = this._boufbowlerSpriteHolder.scaleY = 1.8;
         inGameHolder.addChild(this._boufbowlerSpriteHolder);
         this.initClassSelector();
         cancelButton.addEventListener(MouseEvent.CLICK,this.cancelButtonClickHandler);
         validateButton.addEventListener(MouseEvent.CLICK,this.validateButtonClickHandler);
         boufbowlerName.addEventListener(FocusEvent.FOCUS_OUT,this.boufbowlerNameFocusOutHandler);
         hairColorGrid.addEventListener(ColorGridEvent.CHANGE,this.colorGridCellClickHandler);
         skinColorGrid.addEventListener(ColorGridEvent.CHANGE,this.colorGridCellClickHandler);
         eyesColorGrid.addEventListener(ColorGridEvent.CHANGE,this.colorGridCellClickHandler);
         paletteSelector.list.addEventListener(ItemSelectorList.ITEM_SELECTED,this.paletteSelectorPaletteSelected);
         paletteSelector.list.title = this._translator.getText(LangConstants.PALETTE_SELECTOR_TITLE);
         paletteSelector.setListState(ItemSelectorList.BOTTOM_LEFT);
         paletteSelector.openButton.addEventListener(MouseEvent.CLICK,this.itemSelectorClicked);
         boufbowlerHolder.scaleX = boufbowlerHolder.scaleY = 0.9;
         prevFieldPostureButton.addEventListener(MouseEvent.CLICK,this.changeFieldPostureClicked);
         nextFieldPostureButton.addEventListener(MouseEvent.CLICK,this.changeFieldPostureClicked);
      }
      
      private function initClassSelector() : void
      {
         classSelectorPlaceHolder.addChild(this._classSelector);
         this._classSelector.setTitle(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_CLASSSELECTOR_TITLE));
         this._classSelector.addEventListener(ClassPedestal.CLASS_SELECTED,this.classSelectedHandler,false,0,true);
         this._classSelector.addEventListener(BoufbowlerPictures.SKIN_SELECTED,this.skinSelectedHandler,false,0,true);
      }
      
      private function classSelectedHandler(param1:IndexEvent) : void
      {
         param1.stopPropagation();
         dispatchEvent(new IndexEvent(CLASS_SELECTED,param1.index));
      }
      
      private function skinSelectedHandler(param1:IndexEvent) : void
      {
         param1.stopPropagation();
         var _loc2_:int = param1.index;
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.BOUFBOWLERCUSTOMIZATION_PORTRAIT_CLICKED));
         dispatchEvent(new IndexEvent(SKIN_SELECTED,_loc2_));
      }
      
      private function changeFieldPostureClicked(param1:MouseEvent) : void
      {
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.BOUFBOWLERCUSTOMIZATION_ANIMATIONNAVBUTTON_CLICKED));
      }
      
      private function validateButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.BOUFBOWLERCUSTOMIZATION_OKBUTTON_CLICKED));
      }
      
      private function itemSelectorClicked(param1:MouseEvent) : void
      {
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.CUSTOMIZATION_PALETTESELECTOR_OPEN));
      }
      
      private function paletteSelectorPaletteSelected(param1:ItemSelectedEvent) : void
      {
         param1.preventDefault();
         dispatchEvent(new IndexEvent(SELECTED_PALETTE_CHANGED,param1.item.id));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.CUSTOMIZATION_PALETTESELECTOR_CLOSED));
      }
      
      private function initTexts() : void
      {
         cancelButton.componentLabel = this._translator.getText(LangConstants.CANCEL);
         title = this._translator.getText(LangConstants.BOUFBOWLEREDITOR_TITLE);
         skinLabelIcon.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_SKIN_LABELICON_TOOLTIP));
         hairLabelIcon.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_HAIR_LABELICON_TOOLTIP));
         eyesLabelIcon.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_EYES_LABELICON_TOOLTIP));
         boufbowlerLabel = this._translator.getText(LangConstants.BOUFBOWLEREDITOR_BOUFBOWLER_LABEL);
         paletteSelector.list.title = this._translator.getText(LangConstants.PALETTE_SELECTOR_TITLE);
         paletteSelector.setTooltip(this._translator.getText(LangConstants.PALETTE_SELECTOR_TOOLTIP));
         prevFieldPostureButton.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_POSTURE_PREV_BUTTON_TOOLTIP));
         nextFieldPostureButton.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_POSTURE_NEXT_BUTTON_TOOLTIP));
         refreshButton.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_REFRESH_BUTTON_TOOLTIP));
         validateButton.componentLabel = this._translator.getText(LangConstants.OK);
         validateButton.setTooltip(this._translator.getText(LangConstants.BOUFBOWLEREDITOR_VALIDATE_BUTTON_TOOLTIP));
      }
      
      private function cancelButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new Event(CANCEL_CLICKED));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.BOUFBOWLERCUSTOMIZATION_BACKBUTTON_CLICKED));
      }
      
      private function boufbowlerNameFocusOutHandler(param1:Event) : void
      {
         dispatchEvent(new TextEvent(NAME_CHANGED,false,false,boufbowlerName.text));
      }
      
      private function updateClassOrderInfos(param1:int) : void
      {
         if(param1 == 0)
         {
            orderClassIcon.visible = false;
         }
         else
         {
            orderClassIcon.visible = true;
            orderClassIcon.classIcon = param1;
         }
         if(param1 == 0)
         {
            classOrderDesc = "";
         }
         else
         {
            if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode())
            {
               classOrderDesc = com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverAbilityDescription(param1);
               return;
            }
            classOrderDesc = "<span fontWeight=\"bold\" fontSize=\"12\">" + this._translator.getText(LangConstants.CLASS_ORDER_TITLE) + this._translator.getEnumTranslation(LangConstants.CLASSES_ORDER_NAME_ENUM,param1) + "</span><br />" + this._translator.getEnumTranslation(LangConstants.CLASSES_ORDER_TOOLTIP_DESC_ENUM,param1);
         }
      }
      
      private function updateGauges(param1:IClubBoufbowlerModel) : void
      {
         boufbowlerInfos.airGauge.maxValue = BoufbowlerAttributesModel.MAX_ELEMENT_ATTRIBUTE_VALUE;
         boufbowlerInfos.airGauge.value = param1.attributes.air;
         boufbowlerInfos.airGauge.color = this._colorScheme.getElementColor(Element.AIR);
         boufbowlerInfos.airGauge.setTooltip(this._translator.getText(LangConstants.TEAMPANEL_GAUGE_AIR_TOOLTIP,param1.attributes.air));
         boufbowlerInfos.earthGauge.maxValue = BoufbowlerAttributesModel.MAX_ELEMENT_ATTRIBUTE_VALUE;
         boufbowlerInfos.earthGauge.value = param1.attributes.earth;
         boufbowlerInfos.earthGauge.color = this._colorScheme.getElementColor(Element.EARTH);
         boufbowlerInfos.earthGauge.setTooltip(this._translator.getText(LangConstants.TEAMPANEL_GAUGE_EARTH_TOOLTIP,param1.attributes.earth));
         boufbowlerInfos.fireGauge.maxValue = BoufbowlerAttributesModel.MAX_ELEMENT_ATTRIBUTE_VALUE;
         boufbowlerInfos.fireGauge.value = param1.attributes.fire;
         boufbowlerInfos.fireGauge.color = this._colorScheme.getElementColor(Element.FIRE);
         boufbowlerInfos.fireGauge.setTooltip(this._translator.getText(LangConstants.TEAMPANEL_GAUGE_FIRE_TOOLTIP,param1.attributes.fire));
         boufbowlerInfos.waterGauge.maxValue = BoufbowlerAttributesModel.MAX_ELEMENT_ATTRIBUTE_VALUE;
         boufbowlerInfos.waterGauge.value = param1.attributes.water;
         boufbowlerInfos.waterGauge.color = this._colorScheme.getElementColor(Element.WATER);
         boufbowlerInfos.waterGauge.setTooltip(this._translator.getText(LangConstants.TEAMPANEL_GAUGE_WATER_TOOLTIP,param1.attributes.water));
         boufbowlerInfos.healthTag.attribute = AttributeTag.HEALTH;
         boufbowlerInfos.healthTag.value = param1.attributes.maxHealth.toString();
         boufbowlerInfos.healthTag.setTooltip(this._translator.getText(LangConstants.TEAMPANEL_CARAC_HEALTH_TOOLTIP,param1.attributes.health,param1.attributes.maxHealth));
         boufbowlerInfos.regenTag.attribute = AttributeTag.REGENERATION;
         boufbowlerInfos.regenTag.value = param1.attributes.regeneration.toString();
         boufbowlerInfos.regenTag.setTooltip(this._translator.getText(LangConstants.TEAMPANEL_CARAC_REGEN_TOOLTIP,param1.attributes.regeneration));
      }
      
      private function colorGridCellClickHandler(param1:ColorGridEvent) : void
      {
         var _loc2_:uint = BoufbowlerPaletteItem.HAIR_COLOR;
         if(param1.currentTarget == eyesColorGrid)
         {
            _loc2_ = BoufbowlerPaletteItem.EYE_COLOR;
         }
         else if(param1.currentTarget == skinColorGrid)
         {
            _loc2_ = BoufbowlerPaletteItem.SKIN_COLOR;
         }
         dispatchEvent(new ColorSelectedEvent(SELECTED_COLOR_CHANGED,_loc2_,param1.lineIndex,param1.cellLineIndex));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.CUSTOMIZATION_COLOR_CHOSEN));
      }
   }
}

