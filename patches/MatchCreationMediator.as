package com.ankamagames.boufbowl.client.matchmaking.view
{
   import com.ankamagames.boufbowl.client.application.mediator.BoufbowlMediator;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.matchmaking.event.CreateChallengeEvent;
   import com.ankamagames.boufbowl.client.matchmaking.event.DisplayMatchCreationTypeEvent;
   import com.ankamagames.boufbowl.client.matchmaking.event.MatchCreationEvent;
   import com.ankamagames.boufbowl.client.matchmaking.model.MatchCreationModel;
   import com.ankamagames.boufbowl.client.matchmaking.model.MatchCreationType;
   import com.ankamagames.boufbowl.client.premiumservice.common.event.PremiumContentEvent;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.PremiumContentModel;
   import com.ankamagames.boufbowl.ui.components.matchcreation.MatchCreationTabs;
   import com.ankamagames.xgaming.utils.injection.module.event.DisplayViewEvent;
   import flash.events.Event;
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   import com.ankamagames.xgaming.utils.event.IndexEvent;
   import flash.events.MouseEvent;
   
   public class MatchCreationMediator extends BoufbowlMediator
   {
      
      public static const REQUEST_RANDOM_MATCH:String = "com.ankamagames.boufbowl.client.matchmaking.view.MatchCreationMediator.REQUEST_RANDOM_MATCH";
      
      private var _view:MatchCreationView;

      private var _matchCreation:MatchCreationModel;
      
      public function MatchCreationMediator(param1:MatchCreationView, param2:PremiumContentModel, param3:MatchCreationModel)
      {
         super();
         this._view = param1;
         this._matchCreation = param3;
         this.init(param2,param3);
      }
      
      override public function onRegister() : void
      {
         super.onRegister();
         addModuleListener(PremiumContentModel.ASSETS_UPDATED,this.premiumAssetsUpdatedHandler);
         addModuleListener(MatchCreationModel.CREATION_MODE_CHANGED,this.creationModeChangedHandler);
         addModuleListener(MatchCreationModel.SELECTED_STADIUM_UPDATED,this.selectedStadiumUpdated);
         addViewListener(MatchCreationView.STADIUM_CLICKED,this.stadiumSelected);
         eventMap.mapListener(this._view.tabs.challengeTabButton,MouseEvent.CLICK,this.friendlyTabButtonClickHandler);
         eventMap.mapListener(this._view.tabs.randomTabButton,MouseEvent.CLICK,this.randomTabButtonClickHandler);
         eventMap.mapListener(this._view.backButtonSprite,MouseEvent.CLICK,this.backButtonClickHandler);
         eventMap.mapListener(this._view.tabs.randomTab.playButton,MouseEvent.CLICK,this.randomTabPlayButtonClickHandler);
         eventMap.mapListener(this._view.tabs.challengeTab.playButton,MouseEvent.CLICK,this.challengeTabPlayButtonClickHandler);
      }
      
      private function init(param1:PremiumContentModel, param2:MatchCreationModel) : void
      {
         this._view.updateStadiums(param1.stadiumItems);
         this._view.selectStadium(param2.selectedStadium);
         this.updateCreationMode(param2);
      }
      
      private function premiumAssetsUpdatedHandler(param1:PremiumContentEvent) : void
      {
         this._view.updateStadiums(param1.premiumContent.stadiumItems);
      }
      
      private function creationModeChangedHandler(param1:MatchCreationEvent) : void
      {
         this.updateCreationMode(param1.matchCreation);
      }
      
      private function updateCreationMode(param1:MatchCreationModel) : void
      {
         var _loc2_:String = this.matchCreationModeToTabName(param1.creationType);
         if(_loc2_ != null)
         {
            this._view.tabs.displayTab(_loc2_);
         }
         this._view.serverPageMode(param1.creationType == MatchCreationType.CHALLENGE);
         if(param1.creationType == MatchCreationType.CHALLENGE && param1.guestNickname != null)
         {
            this._view.tabs.challengeTab.opponentName = param1.guestNickname;
         }
      }
      
      private function stadiumSelected(event:IndexEvent) : void
      {
         if(StartUpApplicationCommand.serverMode()) this._matchCreation.selectedStadium=event.index;
         else dispatch(event);
      }

      private function selectedStadiumUpdated(param1:MatchCreationEvent) : void
      {
         this._view.selectStadium(param1.matchCreation.selectedStadium);
      }
      
      private function randomTabButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchToModules(new DisplayMatchCreationTypeEvent(MatchCreationType.RANDOM));
      }
      
      private function friendlyTabButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchToModules(new DisplayMatchCreationTypeEvent(MatchCreationType.CHALLENGE,this._view.tabs.challengeTab.opponentName));
      }
      
      private function tournamentTabButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchToModules(new DisplayMatchCreationTypeEvent(MatchCreationType.TOURNAMENT));
      }
      
      private function randomTabPlayButtonClickHandler(param1:MouseEvent) : void
      {
         if(StartUpApplicationCommand.serverMode()) this._view.submitServerMatch("queue_join");
         else dispatch(new Event(REQUEST_RANDOM_MATCH));
         playSound(InterfaceSoundEvents.MATCHMAKING_PLAYBUTTON_CLICKED);
      }
      
      private function challengeTabPlayButtonClickHandler(param1:MouseEvent) : void
      {
         if(StartUpApplicationCommand.serverMode()) this._view.submitServerMatch("challenge");
         else dispatch(new CreateChallengeEvent(this._view.tabs.challengeTab.opponentName));
         playSound(InterfaceSoundEvents.MATCHMAKING_PLAYBUTTON_CLICKED);
      }
      
      private function backButtonClickHandler(param1:MouseEvent) : void
      {
         dispatch(new DisplayViewEvent(Views.WELCOME));
         playSound(InterfaceSoundEvents.MATCHMAKING_BACKBUTTON_CLICKED);
      }
      
      private function matchCreationModeToTabName(param1:int) : String
      {
         switch(param1)
         {
            case MatchCreationType.RANDOM:
               return MatchCreationTabs.RANDOM;
            case MatchCreationType.CHALLENGE:
               return MatchCreationTabs.CHALLENGE;
            default:
               return null;
         }
      }
   }
}

