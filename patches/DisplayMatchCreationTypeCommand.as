package com.ankamagames.boufbowl.client.matchmaking.controller
{
   import com.ankamagames.boufbowl.client.application.helpwindow.event.HelpWindowEvent;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.matchmaking.event.DisplayMatchCreationTypeEvent;
   import com.ankamagames.boufbowl.client.matchmaking.model.MatchCreationModel;
   import com.ankamagames.boufbowl.client.matchmaking.model.MatchCreationType;
   import com.ankamagames.boufbowl.client.matchmaking.view.Views;
   import com.ankamagames.xgaming.utils.injection.module.event.DisplayViewEvent;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class DisplayMatchCreationTypeCommand extends ModuleCommand
   {
      
      private var _matchCreation:MatchCreationModel;
      
      private var _event:DisplayMatchCreationTypeEvent;
      
      public function DisplayMatchCreationTypeCommand(param1:MatchCreationModel, param2:DisplayMatchCreationTypeEvent)
      {
         super();
         this._matchCreation = param1;
         this._event = param2;
      }
      
      override public function execute() : void
      {
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode() && this._event.matchCreationType != MatchCreationType.CHALLENGE)
         {
            com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverPlay();
            return;
         }
         if(this._event.matchCreationType == MatchCreationType.TOURNAMENT)
         {
            dispatch(new DisplayViewEvent(Views.TOURNAMENT));
            dispatchToModules(new HelpWindowEvent(LangConstants.TOURNAMENT_HELP_TITLE,LangConstants.TOURNAMENT_HELP_CONTENT));
         }
         else
         {
            dispatch(new DisplayViewEvent(Views.MATCH_CREATION));
         }
         this._matchCreation.guestNickname = this._event.nickname;
         this._matchCreation.creationType = this._event.matchCreationType;
      }
   }
}

