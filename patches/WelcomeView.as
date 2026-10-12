package com.ankamagames.boufbowl.client.matchmaking.view
{
   import as3.collections.ILinkedMap;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.club.model.ClubInformation;
   import com.ankamagames.boufbowl.client.club.model.RankingInformation;
   import com.ankamagames.boufbowl.client.club.view.ClubIllustrationView;
   import com.ankamagames.boufbowl.client.club.view.IllustrationViewFactory;
   import com.ankamagames.boufbowl.client.facebook.event.FacebookConnectEvent;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerModel;
   import com.ankamagames.boufbowl.client.premiumservice.common.event.CustomisationSessionRequestEvent;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.PremiumContentModel;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.boufbowl.protocol.CustomisationType;
   import com.ankamagames.boufbowl.ui.client.welcomepanel.WelcomePanelUI;
   import com.ankamagames.boufbowl.ui.components.welcomepanel.boufbowlerslist.BoufbowlerLine;
   import com.ankamagames.boufbowl.ui.components.welcomepanel.premiumservices.PremiumServicesList;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.display.DisplayObject;
   import flash.events.Event;
   import flash.events.MouseEvent;
   
   public class WelcomeView extends WelcomePanelUI
   {
      
      public static const CUSTOMISATION_CLICKED:String = "com.ankamagames.boufbowl.client.matchmaking.view.WelcomeView.CUSTOMISATION_CLICKED";
      
      private var _clubIllustration:ClubIllustrationView;
      
      private var _config:IBoufbowlConfig;
      
      private var _translator:ITranslator;
      
      private var _boufbowlers:ILinkedMap;
      
      private var _facebookConnected:Boolean;
      
      public function WelcomeView(param1:IllustrationViewFactory, param2:IBoufbowlConfig, param3:ITranslator)
      {
         super();
         this._clubIllustration = param1.getClubIllustration();
         this._config = param2;
         this._translator = param3;
         this.init();
      }
      
      internal function updateClubInformations(param1:ClubInformation) : void
      {
         clubCard.teamName = param1.name;
         clubCard.blason.update(param1.sigilCharge,param1.sigilBackground);
         clubCard.blason.updateColors(param1.mainColor,param1.alternateColor,param1.sigilColor);
         clubCard.leagueIcon.league = param1.rankingInformation.league;
      }
      
      internal function updateRanking(param1:RankingInformation) : void
      {
         clubCard.ladderPosition = param1.getLocalizedFullRankInfos(this._translator);
         clubCard.stats = param1.getLocalizedVNDString(this._translator);
         clubCard.totalScore = "";
         clubCard.leagueIcon.visible = param1.isRanked();
      }
      
      internal function get facebookConnected() : Boolean
      {
         return this._facebookConnected;
      }
      
      internal function set facebookConnected(param1:Boolean) : void
      {
         this._facebookConnected = param1;
         if(!this._config.facebookEnabled) { facebookButton.visible = false; return; }
         if(this._facebookConnected)
         {
            facebookButton.visible = false;
         }
         else
         {
            facebookButton.visible = true;
            facebookButton.componentLabel = this._translator.getText(LangConstants.FACEBOOK_CONNECTION_BUTTON);
            facebookButton.setTooltip(this._translator.getText(LangConstants.FACEBOOK_CONNECTION_BUTTON_TOOLTIP) + "<br />" + this._translator.getText(LangConstants.FACEBOOK_SCREENSHOT_BUTTON_TOOLTIP));
         }
      }
      
      internal function updateClub(param1:ClubInformation, param2:ILinkedMap, param3:Boolean) : void
      {
         this._boufbowlers = param2;
         this.updateClubInformations(param1);
         this.updateRanking(param1.rankingInformation);
         this.updateIllustration();
         this.updateBoufbowlerList();
         premiumServicesList.setState(param3 ? PremiumServicesList.PREDEF_CLUB : PremiumServicesList.CUSTO_CLUB);
      }
      
      internal function updateCredits(param1:PremiumContentModel) : void
      {
         premiumServicesList.setTeamCreationCredits(param1.getCustomisationCredits(CustomisationType.FULL_TEAM),this._translator.getText(LangConstants.PREMIUMSERVICE_CREDIT_COUNT_TOOLTIP,param1.getCustomisationCredits(CustomisationType.FULL_TEAM),this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_ENUM,CustomisationType.FULL_TEAM)));
         premiumServicesList.setTeamLookCutomisationCredits(param1.getCustomisationCredits(CustomisationType.CLUB_APPEARANCE),this._translator.getText(LangConstants.PREMIUMSERVICE_CREDIT_COUNT_TOOLTIP,param1.getCustomisationCredits(CustomisationType.CLUB_APPEARANCE),this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_ENUM,CustomisationType.CLUB_APPEARANCE)));
         premiumServicesList.setTeamCompositionCredits(param1.getCustomisationCredits(CustomisationType.BOUFBOWLER_ATTRIBUTES),this._translator.getText(LangConstants.PREMIUMSERVICE_CREDIT_COUNT_TOOLTIP,param1.getCustomisationCredits(CustomisationType.BOUFBOWLER_ATTRIBUTES),this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_ENUM,CustomisationType.BOUFBOWLER_ATTRIBUTES)));
         premiumServicesList.setBoufbowlerCustomisationCredits(param1.getCustomisationCredits(CustomisationType.BOUFBOWLER_APPEARANCE),this._translator.getText(LangConstants.PREMIUMSERVICE_CREDIT_COUNT_TOOLTIP,param1.getCustomisationCredits(CustomisationType.BOUFBOWLER_APPEARANCE),this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_ENUM,CustomisationType.BOUFBOWLER_APPEARANCE)));
      }
      
      private function init() : void
      {
         playButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_WELCOME_PLAY_BUTTON);
         ladderButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_LADDER_BUTTON);
         standardTutoButton.componentLabel = this._translator.getText(LangConstants.LOGIN_TUTO_BUTTON);
         advancedTutoButton.componentLabel = this._translator.getText(LangConstants.LOGIN_ADVANCEDTUTO_BUTTON);
         facebookButton.visible = this._config.facebookEnabled;
         facebookButton.componentLabel = this._translator.getText(LangConstants.FACEBOOK_CONNECTION_BUTTON);
         facebookButton.addEventListener(MouseEvent.CLICK,this.facebookButtonClickHandler);
         premiumServicesList.setEditTeamButtonLabel(this._translator.getText(LangConstants.MODIFY_TEAM_BUTTON),this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_DETAILS_ENUM,CustomisationType.CLUB_APPEARANCE));
         premiumServicesList.setCreateTeamButtonLabel(this._translator.getText(LangConstants.NEW_TEAM_BUTTON),this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_DETAILS_ENUM,CustomisationType.FULL_TEAM));
         premiumServicesList.explain = this._translator.getText(LangConstants.WELCOMEPANEL_FIRST_CUSTO_ESPLANATION);
         this.initBoufbowlerList();
         this.initTeamEditon();
         advancedTutoButton.visible = false;
         tournamentButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_TOURNAMENT_BUTTON);
      }
      
      private function initBoufbowlerList() : void
      {
         var _loc2_:BoufbowlerLine = null;
         var _loc1_:int = 0;
         while(_loc1_ < 10)
         {
            _loc2_ = premiumServicesList.boufbowlersList.getLine(_loc1_);
            _loc2_.appearanceCustomisationButton.setTooltip(this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_DETAILS_ENUM,4));
            _loc2_.attributesCustomisationButton.setTooltip(this._translator.getEnumTranslation(LangConstants.WELCOMEPANEL_PREMIUMSERVICE_CUSTOMISATION_DETAILS_ENUM,3));
            _loc2_.appearanceCustomisationButton.visible = this._config.premiumServiceEnabled;
            _loc2_.appearanceCustomisationButton.addEventListener(MouseEvent.CLICK,this.appearanceCustomisationButtonClickHandler);
            _loc2_.attributesCustomisationButton.visible = this._config.premiumServiceEnabled;
            _loc2_.attributesCustomisationButton.addEventListener(MouseEvent.CLICK,this.attributesCustomisationButtonClickHandler);
            _loc1_++;
         }
      }
      
      private function initTeamEditon() : void
      {
         premiumServicesList.setPremiumServiceEnabled(this._config.premiumServiceEnabled);
         premiumServicesList.setEditTeamCallback(this.editTeamButtonClickHandler);
         premiumServicesList.setNewTeamCallback(this.newTeamButtonClickHandler);
      }
      
      private function facebookButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new Event(FacebookConnectEvent.CONNECT));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.WELCOMEPANEL_FACEBOOKBUTTON_CLICKED));
      }
      
      private function editTeamButtonClickHandler() : void
      {
         dispatchEvent(new CustomisationSessionRequestEvent(CUSTOMISATION_CLICKED,CustomisationType.CLUB_APPEARANCE));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.WELCOMEPANEL_CUSTOMIZETEAMBUTTON_CLICKED));
      }
      
      private function newTeamButtonClickHandler() : void
      {
         dispatchEvent(new CustomisationSessionRequestEvent(CUSTOMISATION_CLICKED,CustomisationType.FULL_TEAM));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.WELCOMEPANEL_CREATENEWTEAMBUTTON_CLICKED));
      }
      
      private function updateIllustration() : void
      {
         this._clubIllustration.update(this._boufbowlers.toArray());
         illustrationHolder.addChild(this._clubIllustration);
         illustrationHolder.scaleX = illustrationHolder.scaleY = 0.85;
      }
      
      private function updateBoufbowlerList() : void
      {
         var _loc3_:IBoufbowlerModel = null;
         var _loc4_:BoufbowlerLine = null;
         premiumServicesList.boxTitle = this._translator.getText(LangConstants.MATCHMAKING_WELCOME_BOUFBOWLER_LIST_LABEL);
         var _loc1_:* = 0;
         var _loc2_:IIterator = this._boufbowlers.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            _loc4_ = premiumServicesList.boufbowlersList.getLine(_loc1_++);
            _loc4_.update(_loc3_.id,_loc3_.name,_loc3_.skinId);
         }
      }
      
      private function appearanceCustomisationButtonClickHandler(param1:MouseEvent) : void
      {
         var _loc2_:BoufbowlerLine = BoufbowlerLine(DisplayObject(param1.currentTarget).parent);
         if(_loc2_.id == null)
         {
            return;
         }
         dispatchEvent(new CustomisationSessionRequestEvent(CUSTOMISATION_CLICKED,CustomisationType.BOUFBOWLER_APPEARANCE,_loc2_.id));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.WELCOMEPANEL_CUSTOMIZEBOUFBOWLERBUTTON_CLICKED));
      }
      
      private function attributesCustomisationButtonClickHandler(param1:MouseEvent) : void
      {
         var _loc2_:BoufbowlerLine = BoufbowlerLine(DisplayObject(param1.currentTarget).parent);
         if(_loc2_.id == null)
         {
            return;
         }
         dispatchEvent(new CustomisationSessionRequestEvent(CUSTOMISATION_CLICKED,CustomisationType.BOUFBOWLER_ATTRIBUTES,_loc2_.id));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.WELCOMEPANEL_REPLACEBOUFBOWLERBUTTON_CLICKED));
      }
   }
}

