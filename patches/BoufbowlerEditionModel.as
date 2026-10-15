package com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.model
{
   import as3.collections.IArrayList;
   import as3.collections.ILinkedMap;
   import as3.collections.IMap;
   import as3.collections.LinkedMap;
   import as3.collections.iterators.IIterator;
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.client.boufbowler.model.IClassAttributesModel;
   import com.ankamagames.boufbowl.client.club.model.ClubBoufbowlerFactory;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.strategic.model.BoufbowlerAttributesModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerAttributesModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IClubBoufbowlerModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.RulesConstants;
   import com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.event.BoufbowlerEditionEvent;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.BasePaletteItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.BoufbowlerPaletteItem;
   import com.ankamagames.boufbowl.protocol.BoufbowlerClass;
   import com.ankamagames.boufbowl.protocol.CustomisationType;
   import com.ankamagames.boufbowl.protocol.Gender;
   import com.ankamagames.boufbowl.protocol.ItemAvailability;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.netease.protobuf.Int64;
   import org.robotlegs.mvcs.Actor;
   
   [Inject(name="displayableAnimations")]
   public class BoufbowlerEditionModel extends Actor
   {
      
      public static const NAME_UPDATED:String = "com.ankamagames.boufbowl.client.premiumservice.model.BoufbowlerEditionModel.NAME_UPDATED";
      
      public static const ATTRIBUTES_UPDATED:String = "com.ankamagames.boufbowl.client.premiumservice.model.BoufbowlerEditionModel.ATTRIBUTES_UPDATED";
      
      public static const COLORS_UPDATED:String = "com.ankamagames.boufbowl.client.premiumservice.model.BoufbowlerEditionModel.COLORS_UPDATED";
      
      public static const ANIMATION_UPDATED:String = "com.ankamagames.boufbowl.client.premiumservice.model.BoufbowlerEditionModel.ANIMATION_UPDATED";
      
      public static const APPLICABLE_PALETTES_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.model.BoufbowlerEditionModel.APPLICABLE_PALETTES_CHANGED";
      
      public static const SELECTED_PALETTE_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.model.BoufbowlerEditionModel.PALETTE_CHANGED";
      
      public static const BOUFBOWLERS_LIST_CHANGED:String = "com.ankamagames.boufbowl.client.premiumservice.model.BoufbowlerEditionModel.BOUFBOWLERS_AVAILABILITY_CHANGED";
      
      private var _currentUniqueNameAutoFilled:Boolean;
      
      private var _translator:ITranslator;
      
      private var _displayableAnimations:IArrayList;
      
      private var _club:ClubModel;
      
      private var _clubBoufbowlerFactory:ClubBoufbowlerFactory;
      
      private var _rulesConstants:RulesConstants;
      
      private var _customisationType:int;
      
      private var _boufbowlerId:Int64;
      
      private var _customizedBoufbowler:IClubBoufbowlerModel;
      
      private var _customizedClub:ClubModel;
      
      private var _currentName:String;
      
      private var _currentGender:int;
      
      private var _currentBoufbowlerClass:int;
      
      private var _currentUniqueCharacter:uint;
      
      private var _currentHairColorId:int;
      
      private var _currentSkinColorId:int;
      
      private var _currentEyeColorId:int;
      
      private var _currentHairColor:Color3;
      
      private var _currentSkinColor:Color3;
      
      private var _currentEyeColor:Color3;
      
      private var _availablePalettes:ILinkedMap;
      
      private var _applicablePalettes:ILinkedMap;
      
      private var _currentPalette:BoufbowlerPaletteItem;
      
      private var _currentAnimationIndex:int;
      
      private var _boufbowlerBySkinId:IMap;
      
      public function BoufbowlerEditionModel(param1:IArrayList, param2:RulesConstants, param3:ClubBoufbowlerFactory, param4:ITranslator)
      {
         super();
         this._displayableAnimations = param1;
         this._rulesConstants = param2;
         this._clubBoufbowlerFactory = param3;
         this._translator = param4;
         this.init();
      }
      
      public function get customisationType() : int
      {
         return this._customisationType;
      }
      
      public function set boufbowlerName(param1:String) : void
      {
         this._currentName = param1;
         this._currentUniqueNameAutoFilled = false;
         this.updateBoufbowler();
         this.updated(NAME_UPDATED);
      }
      
      public function get customizedBoufbowler() : IClubBoufbowlerModel
      {
         return this._customizedBoufbowler;
      }
      
      public function get customizedClub() : ClubModel
      {
         return this._customizedClub;
      }
      
      public function get currentPalette() : BoufbowlerPaletteItem
      {
         return this._currentPalette;
      }
      
      public function get currentAnimation() : AnimationKey
      {
         return this._displayableAnimations.getItemAt(this._currentAnimationIndex);
      }
      
      public function set availablePalettes(param1:ILinkedMap) : void
      {
         this._availablePalettes = param1;
         this.updateApplicablePalettes();
      }
      
      public function get boufbowlerBySkinId() : IMap
      {
         return this._boufbowlerBySkinId;
      }
      
      public function set boufbowlerBySkinId(param1:IMap) : void
      {
         this._boufbowlerBySkinId = param1;
         this.updated(BOUFBOWLERS_LIST_CHANGED);
      }
      
      public function get classChangeAllowed() : Boolean
      {
         return this.customisationType != CustomisationType.BOUFBOWLER_APPEARANCE;
      }
      
      public function get uniqueCharactersInClub() : Array
      {
         return this._customizedClub.uniqueCharacters;
      }
      
      public function get applicablePalettes() : ILinkedMap
      {
         return this._applicablePalettes;
      }
      
      public function get hairColorId() : int
      {
         return this._currentHairColorId;
      }
      
      public function get skinColorId() : int
      {
         return this._currentSkinColorId;
      }
      
      public function get eyeColorId() : int
      {
         return this._currentEyeColorId;
      }
      
      public function setBoufbowlerAttributes(param1:int, param2:int, param3:uint) : void
      {
         if(!this.classChangeAllowed && (param1 != this._currentBoufbowlerClass || param3 != this._currentUniqueCharacter)) return;
         this._currentBoufbowlerClass = param1;
         this._currentGender = param2;
         this._currentUniqueCharacter = param3;
         if(param3 > 0 && (this._currentUniqueNameAutoFilled || this._currentName == "" || this._currentName == null))
         {
            this._currentName = this._translator.getEnumTranslation(LangConstants.UNIQUE_CHARACTER_NAME_ENUM,param3);
            this._currentUniqueNameAutoFilled = true;
         }
         else if(this._currentUniqueNameAutoFilled)
         {
            this._currentName = "";
            this._currentUniqueNameAutoFilled = false;
         }
         this.updateApplicablePalettes(true);
         this.updated(ATTRIBUTES_UPDATED);
         this.updateBoufbowler();
         this.updated(NAME_UPDATED);
      }
      
      public function selectPalette(param1:int, param2:Boolean = false) : void
      {
         var _loc3_:BoufbowlerPaletteItem = this._applicablePalettes.getItem(param1);
         if(_loc3_ == null)
         {
            throw new IllegalStateError("Palette with id " + param1 + " doesn\'t exist in the applicablePalettes lists");
         }
         this._currentPalette = _loc3_;
         this.updateColorsId(param2);
         this._currentHairColorId = this.validColorIndex(BoufbowlerPaletteItem.HAIR_COLOR,this._currentHairColorId);
         this._currentEyeColorId = this.validColorIndex(BoufbowlerPaletteItem.EYE_COLOR,this._currentEyeColorId);
         this._currentSkinColorId = this.validColorIndex(BoufbowlerPaletteItem.SKIN_COLOR,this._currentSkinColorId);
         this.updated(SELECTED_PALETTE_CHANGED);
         this.updateColors();
      }
      
      public function selectColor(param1:uint, param2:uint) : void
      {
         if(param1 == BoufbowlerPaletteItem.HAIR_COLOR)
         {
            this._currentHairColorId = param2;
         }
         else if(param1 == BoufbowlerPaletteItem.EYE_COLOR)
         {
            this._currentEyeColorId = param2;
         }
         else if(param1 == BoufbowlerPaletteItem.SKIN_COLOR)
         {
            this._currentSkinColorId = param2;
         }
         this.updateColors();
      }
      
      public function displayPreviousAnimation() : void
      {
         --this._currentAnimationIndex;
         if(this._currentAnimationIndex < 0)
         {
            this._currentAnimationIndex = this._displayableAnimations.numItems - 1;
         }
         this.updated(ANIMATION_UPDATED);
      }
      
      public function displayNextAnimation() : void
      {
         ++this._currentAnimationIndex;
         if(this._currentAnimationIndex >= this._displayableAnimations.numItems)
         {
            this._currentAnimationIndex = 0;
         }
         this.updated(ANIMATION_UPDATED);
      }
      
      public function setup(param1:int, param2:ClubModel, param3:Int64) : void
      {
         this._customisationType = param1;
         this._club = param2;
         this._boufbowlerId = param3;
         var _loc4_:IClubBoufbowlerModel = this._club.getBoufbowler(this._boufbowlerId);
         this._currentName = _loc4_.name;
         this._currentGender = _loc4_.gender;
         this._currentBoufbowlerClass = _loc4_.boufbowlerClass;
         this._currentUniqueCharacter = _loc4_.isUniqueCharacter ? uint(_loc4_.uniqueCharacter) : 0;
         if(_loc4_.hasPaletteId)
         {
            this._currentPalette = this._availablePalettes.getItem(_loc4_.paletteId);
         }
         if(this._currentPalette == null)
         {
            this._currentPalette = this.emptyPalette();
         }
         this._currentHairColor = _loc4_.hairColor;
         this._currentSkinColor = _loc4_.skinColor;
         this._currentEyeColor = _loc4_.eyeColor;
         this.updateBoufbowler();
         this.updateApplicablePalettes();
         this.updated(NAME_UPDATED);
         this.updated(ATTRIBUTES_UPDATED);
         this.updated(COLORS_UPDATED);
      }
      
      private function init() : void
      {
         this._currentGender = Gender.MALE;
         this._currentBoufbowlerClass = BoufbowlerClass.IOP;
         this._currentUniqueCharacter = 0;
         this._currentAnimationIndex = 0;
      }
      
      private function emptyPalette() : BoufbowlerPaletteItem
      {
         return new BoufbowlerPaletteItem(ItemAvailability.BASE,0,0,0,0,[],[],[]);
      }
      
      private function updateApplicablePalettes(param1:Boolean = false) : void
      {
         var _loc3_:BoufbowlerPaletteItem = null;
         this._applicablePalettes = new LinkedMap();
         // Include every style for this class; the first remains its default.
         var _loc2_:IIterator = this._availablePalettes.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(this.isDefaultForUniqueCharacter(this._currentUniqueCharacter,_loc3_) || this.isDefaultForClass(this._currentBoufbowlerClass,this._currentUniqueCharacter,_loc3_))
            {
               this._applicablePalettes.addItem(_loc3_.id,_loc3_);
            }
         }
         _loc2_ = this._availablePalettes.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(this.isNotDefault(_loc3_))
            {
               this._applicablePalettes.addItem(_loc3_.id,_loc3_);
            }
         }
         this.updated(APPLICABLE_PALETTES_CHANGED);
         if(this._currentPalette == null || !this._applicablePalettes.hasKey(this._currentPalette.id) || this._currentPalette.availability == ItemAvailability.LOCKED || param1)
         {
            this.selectPalette(BasePaletteItem(this._applicablePalettes.getFirstItem()).id,true);
         }
         else
         {
            this.selectPalette(this._currentPalette.id);
         }
      }
      
      private function isDefaultForUniqueCharacter(param1:int, param2:BoufbowlerPaletteItem) : Boolean
      {
         return param1 != 0 && param2.isDefaultForUniqueCharacter && param1 == param2.defaultForUniqueCharacter;
      }
      
      private function isDefaultForClass(param1:int, param2:int, param3:BoufbowlerPaletteItem) : Boolean
      {
         return param2 == 0 && param1 != 0 && param3.isDefaultForClass && param1 == param3.defaultForClass;
      }
      
      private function isNotDefault(param1:BoufbowlerPaletteItem) : Boolean
      {
         return !param1.isDefaultForClass && !param1.isDefaultForUniqueCharacter;
      }
      
      private function updateColorsId(param1:Boolean = false) : void
      {
         var _loc2_:int = 0;
         var _loc3_:int = 0;
         var _loc4_:int = 0;
         if(this._customizedBoufbowler == null || param1)
         {
            this._currentHairColorId = this._currentPalette.getDefaultHairColorId(this._currentUniqueCharacter,this._currentGender);
            this._currentEyeColorId = this._currentPalette.getDefaultEyeColorId(this._currentUniqueCharacter,this._currentGender);
            this._currentSkinColorId = this._currentPalette.getDefaultSkinColorId(this._currentUniqueCharacter,this._currentGender);
         }
         else
         {
            _loc2_ = this._currentPalette.getColorIndex(BoufbowlerPaletteItem.HAIR_COLOR,this._currentHairColor);
            this._currentHairColorId = _loc2_ != -1 ? _loc2_ : this._currentPalette.getDefaultHairColorId(this._currentUniqueCharacter,this._currentGender);
            _loc3_ = this._currentPalette.getColorIndex(BoufbowlerPaletteItem.EYE_COLOR,this._currentEyeColor);
            this._currentEyeColorId = _loc3_ != -1 ? _loc3_ : this._currentPalette.getDefaultEyeColorId(this._currentUniqueCharacter,this._currentGender);
            _loc4_ = this._currentPalette.getColorIndex(BoufbowlerPaletteItem.SKIN_COLOR,this._currentSkinColor);
            this._currentSkinColorId = _loc4_ != -1 ? _loc4_ : this._currentPalette.getDefaultSkinColorId(this._currentUniqueCharacter,this._currentGender);
         }
      }
      
      private function validColorIndex(kind:uint, index:int) : int
      {
         var colors:Array=this._currentPalette.getColorArray(kind);
         return index >= 0 && index < colors.length ? index : 0;
      }

      private function updateColors() : void
      {
         // A previous palette can have more swatches. Never retain an invalid index.
         this._currentHairColorId = this.validColorIndex(BoufbowlerPaletteItem.HAIR_COLOR,this._currentHairColorId);
         this._currentEyeColorId = this.validColorIndex(BoufbowlerPaletteItem.EYE_COLOR,this._currentEyeColorId);
         this._currentSkinColorId = this.validColorIndex(BoufbowlerPaletteItem.SKIN_COLOR,this._currentSkinColorId);
         this._currentHairColor = this._currentPalette.getColor(BoufbowlerPaletteItem.HAIR_COLOR,this._currentHairColorId);
         this._currentEyeColor = this._currentPalette.getColor(BoufbowlerPaletteItem.EYE_COLOR,this._currentEyeColorId);
         this._currentSkinColor = this._currentPalette.getColor(BoufbowlerPaletteItem.SKIN_COLOR,this._currentSkinColorId);
         this.updateBoufbowler();
         this.updated(COLORS_UPDATED);
      }
      
      private function updateBoufbowler() : void
      {
         var _loc3_:IBoufbowlerModel = null;
         if(this._club == null)
         {
            return;
         }
         this._customizedBoufbowler = this._clubBoufbowlerFactory.createBoufbowler(this._boufbowlerId,this._currentName,this._currentBoufbowlerClass,this._currentGender,this._currentUniqueCharacter,this._currentPalette.id,ItemAvailability.BASE,this._currentHairColor,this._currentSkinColor,this._currentEyeColor,this._club.clubInformation.mainColor,this.getBoufbowlerAttributes(this._currentBoufbowlerClass));
         var _loc1_:ILinkedMap = new LinkedMap();
         var _loc2_:IIterator = this._club.boufbowlers.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(_loc3_.id.equals(this._boufbowlerId))
            {
               _loc1_.addItem(this._customizedBoufbowler.id,this._customizedBoufbowler);
            }
            else
            {
               _loc1_.addItem(_loc3_.id,_loc3_);
            }
         }
         this._customizedClub = new ClubModel();
         this._customizedClub.setup(this._club.clubInformation,_loc1_,false);
      }
      
      private function getBoufbowlerAttributes(param1:int) : IBoufbowlerAttributesModel
      {
         var _loc2_:IClassAttributesModel = this._rulesConstants.getClassAttributes(param1);
         if(_loc2_ != null)
         {
            return _loc2_.boufbowlerAttributes;
         }
         return new BoufbowlerAttributesModel(0,0,0,0,0,0);
      }
      
      private function updated(param1:String) : void
      {
         dispatch(new BoufbowlerEditionEvent(param1,this));
      }
   }
}

