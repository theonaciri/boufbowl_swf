package com.ankamagames.boufbowl.client.matchmaking.view.tournament
{
   import as3.collections.IList;
   import as3.collections.IMap;
   import as3.collections.LinkedList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.components.matchcreation.tournament.TournamentUI;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.matchmaking.model.ServerTime;
   import com.ankamagames.boufbowl.client.matchmaking.model.TournamentData;
   import com.ankamagames.boufbowl.client.matchmaking.model.TournamentNameBuilder;
   import com.ankamagames.boufbowl.client.matchmaking.model.TournamentRoundData;
   import com.ankamagames.boufbowl.client.matchmaking.model.TournamentState;
   import com.ankamagames.boufbowl.client.matchmaking.view.StadiumDescriptionTextBuilder;
   import com.ankamagames.xgaming.ui.components.list.ItemSelectorList;
   import com.ankamagames.xgaming.ui.event.ItemSelectedEvent;
   import com.ankamagames.xgaming.utils.event.Index64Event;
   import com.ankamagames.xgaming.utils.event.IndexEvent;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.string.StringUtils;
   import flash.events.Event;
   import flash.events.MouseEvent;
   
   public class TournamentView extends TournamentUI
   {
      
      public static const TOURNAMENT_STATE_CLICKED:String = "com.ankamagames.boufbowl.client.matchmaking.view.TournamentTabView.TOURNAMENT_STATE_CLICKED";
      
      public static const SELECT_TOURNAMENT:String = "com.ankamagames.boufbowl.client.matchmaking.view.TournamentTabView.SELECT_TOURNAMENT";
      
      public static const REQUEST_TOURNAMENT_LADDER:String = "com.ankamagames.boufbowl.client.matchmaking.view.TournamentTabView.REQUEST_TOURNAMENT_LADDER";
      
      private var _rewardTooltipFactory:TournamentRewardTooltipFactory;
      
      private var _rewardElements:TournamentTextZoneRewardElements;
      
      private var _miniLadder:TournamentMiniLadderUIImpl;
      
      private var _stadiumDescriptionTextBuilder:StadiumDescriptionTextBuilder;
      
      private var _translator:ITranslator;
      
      private var _tournamentNameBuilder:TournamentNameBuilder;
      
      private var _serverTime:ServerTime;
      
      private var _countdown:CountdownModel;
      private var _leagueCountdown:Boolean = false;
      private var _qualificationCountdown:Boolean = false;
      
      public function TournamentView(param1:StadiumDescriptionTextBuilder, param2:ITranslator, param3:TournamentNameBuilder, param4:ServerTime, param5:CountdownModel, param6:TournamentMiniLadderUIImpl, param7:TournamentTextZoneRewardElements, param8:TournamentRewardTooltipFactory)
      {
         super();
         this._stadiumDescriptionTextBuilder = param1;
         this._translator = param2;
         this._tournamentNameBuilder = param3;
         this._serverTime = param4;
         this._countdown = param5;
         this._miniLadder = param6;
         this._rewardElements = param7;
         this._rewardTooltipFactory = param8;
         this.init();
      }
      
      protected function countdownTickHandler(param1:Event) : void
      {
         countdown.dayField = this._countdown.day;
         countdown.timeField = this._countdown.time;
         if(this._leagueCountdown) roundsProgression = this._translator.getText(this._qualificationCountdown ? "tournament_qualification_remaining" : "tournament_time_remaining",this._countdown.time);
      }
      
      internal function udapteTicketCount(param1:uint) : void
      {
         ticketsButton.componentLabel = "x" + param1;
      }
      
      internal function updateTournamentContent(param1:int, param2:TournamentData, param3:IMap, param4:IMap, param5:Boolean) : void
      {
         this.updatePlayButton(param1,param2);
         this.updateTournamentStateButtons(param1,param5);
         content.visible = param2 != null;
         if(param2 == null)
         {
            content.visible = false;
            return;
         }
         content.visible = true;
         this.updateParticipantCount(param2);
         this.updateSummary(param2);
         this.updateListAndTitle(param1,param2,param3,param4);
         this.updateTimeGauge(param2,param1);
         this.updateStadiumInfos(param2);
         this.updateRewardsInfos(param2);
         this.updateRules(param2);
      }
      
      internal function refreshTimeGauge(param1:TournamentData, param2:int) : void
      {
         this.updateTimeGauge(param1,param2);
      }
      
      private function updateRules(param1:TournamentData) : void
      {
         if(this._serverTime.getTime() > param1.endTime && !param1.closed)
         {
            tournamentRules = this._translator.getText(LangConstants.TOURNAMENT_CLOSED_STILL_RUNNING);
         }
         else
         {
            tournamentRules = "<b>" + this._translator.getText(LangConstants.TOURNAMENT_PRICE_RULE,param1.price) + "</b><br />" + this._translator.getText(LangConstants.TOURNAMENT_ELIMINATION_RULE);
         }
      }
      
      private function updateParticipantCount(param1:TournamentData) : void
      {
         if(param1.state == TournamentState.FUTURE)
         {
            participantCount = "";
         }
         else if(param1.state == TournamentState.RUNNING)
         {
            participantCount = this._translator.getText(LangConstants.TOURNAMENT_MINILADDER_RUNNING_PARTICIPANT_COUNT,param1.participantsInTheRunCount,param1.participantsCount);
         }
         else
         {
            participantCount = this._translator.getText(LangConstants.TOURNAMENT_MINILADDER_PAST_PARTICIPANT_COUNT,param1.participantsCount);
         }
      }
      
      private function updateSummary(param1:TournamentData) : void
      {
         var _loc2_:Number = NaN;
         var _loc3_:TournamentRoundData = null;
         this._leagueCountdown = false;this._qualificationCountdown=false;
         if(param1.state == TournamentState.RUNNING && param1.hasRounds)
         {
            this._miniLadder.visible = false;
            countdown.visible = true;
            _loc2_ = this._serverTime.getTime();
            _loc3_ = param1.getRound(_loc2_);
            if(_loc3_ == null)
            {
               this.resetCountdown();
            }
            else if(_loc2_ < _loc3_.startTime)
            {
               this.startCountdown(_loc3_.startTime,this._translator.getText(LangConstants.TOURNAMENT_COUNTDOWN_TOP),this._translator.getText(LangConstants.TOURNAMENT_ROUND_START_COUNTDOWN_BOTTOM));
            }
            else
            {
               this.startCountdown(_loc3_.endTime,this._translator.getText(LangConstants.TOURNAMENT_COUNTDOWN_TOP),this._translator.getText(LangConstants.TOURNAMENT_ROUND_END_COUNTDOWN_BOTTOM));
            }
         }
         else if(param1.state == TournamentState.FUTURE)
         {
            this._miniLadder.visible = false;
            countdown.visible = true;
            this.startCountdown(param1.startTime,this._translator.getText(LangConstants.TOURNAMENT_COUNTDOWN_TOP),this._translator.getText(LangConstants.TOURNAMENT_COUNTDOWN_BOTTOM));
         }
         else
         {
            countdown.visible = false;
            this._miniLadder.visible = true;
            this.resetCountdown();
            this._miniLadder.update(param1);
            if(param1.state == TournamentState.RUNNING) {
               this._leagueCountdown = true;
               var metadata:Object=com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverTournamentDetails(param1.tournamentId);
               this._qualificationCountdown=metadata != null && int(metadata.round)==0;
               this._countdown.startCountDown(this._qualificationCountdown ? Number(metadata.end)*1000 : param1.endTime);
            }
         }
      }
      
      private function startCountdown(param1:Number, param2:String, param3:String) : void
      {
         this._countdown.startCountDown(param1);
         countdown.topField = param2;
         countdown.andField = this._translator.getText(LangConstants.TOURNAMENT_COUNTDOWN_AND);
         countdown.bottomField = param3;
      }
      
      private function resetCountdown() : void
      {
         this._countdown.stopCountDown();
         countdown.topField = countdown.dayField = countdown.andField = countdown.timeField = countdown.bottomField = "";
      }
      
      private function updateRewardsInfos(param1:TournamentData) : void
      {
         rewardsPresenter.updateRewards(param1.firstThresholdReward,param1.secondThresholdReward,param1.thirdThresholdReward,param1.fourthThresholdReward);
         rewardsPresenter.setTooltip(this._rewardTooltipFactory.getTooltip(param1),this._rewardElements.elementsList);
      }
      
      private function updateStadiumInfos(param1:TournamentData) : void
      {
         stadium.setStadium(param1.stadium);
         stadiumName = this._translator.getEnumTranslation(LangConstants.STADIUM_NAME_ENUM,param1.stadium);
         stadiumRules = this._stadiumDescriptionTextBuilder.buildDescription(param1.stadium);
      }
      
      private function updateListAndTitle(param1:int, param2:TournamentData, param3:IMap, param4:IMap) : void
      {
         if(param1 == TournamentState.RUNNING)
         {
            tournamentList.visible = false;
            tournamentNameBackground.visible = true;
            tournamentNameField.visible = true;
            tournamentNameField.text = this._tournamentNameBuilder.computeTournamentName(param2.tournamentType,param2.startTime,param2.endTime);
         }
         else
         {
            tournamentNameBackground.visible = false;
            tournamentNameField.visible = false;
            tournamentList.visible = true;
            tournamentList.setListItems(this.buildTournamentListItems(param1 == TournamentState.PAST ? param3 : param4));
            tournamentList.openButton.componentLabel = this._tournamentNameBuilder.computeTournamentName(param2.tournamentType,param2.startTime,param2.endTime);
         }
      }
      
      private function updateTimeGauge(param1:TournamentData, param2:int) : void
      {
         var _loc3_:Number = NaN;
         var _loc4_:TournamentRoundData = null;
         var _loc5_:int = 0;
         var _loc6_:int = 0;
         timeGauge.startTime = this.formatTime(param1.startTime);
         timeGauge.endTime = this.formatTime(param1.endTime);
         if(param2 == TournamentState.RUNNING)
         {
            _loc3_ = (this._serverTime.getTime() - param1.startTime) / (param1.endTime - param1.startTime);
            if(_loc3_ < 0)
            {
               _loc3_ = 0;
            }
            else if(_loc3_ > 1)
            {
               _loc3_ = 1;
            }
            timeGauge.progress = _loc3_;
         }
         else if(param2 == TournamentState.PAST)
         {
            timeGauge.progress = 1;
         }
         else if(param2 == TournamentState.FUTURE)
         {
            timeGauge.progress = 0;
         }
         if(!param1.hasRounds)
         {
            roundsProgression = this._leagueCountdown ? this._translator.getText(this._qualificationCountdown ? "tournament_qualification_remaining" : "tournament_time_remaining",this._countdown.time) : "";
         }
         else
         {
            _loc4_ = param1.getRound(this._serverTime.getTime());
            if(_loc4_ != null)
            {
               _loc5_ = param1.getRoundIndex(_loc4_);
               _loc6_ = int(param1.rounds.numItems);
               roundsProgression = this._translator.getText(LangConstants.TOURNAMENT_ROUND_PROGRESSION,_loc5_ + 1,_loc6_);
            }
            else if(this._serverTime.getTime() > param1.endTime && !param1.closed)
            {
               roundsProgression = this._translator.getText(LangConstants.TOURNAMENT_ROUND_NOMORE);
            }
            else
            {
               roundsProgression = "";
            }
         }
      }
      
      private function updatePlayButton(param1:int, param2:TournamentData) : void
      {
         if(param2 == null)
         {
            playButton.visible = false;
            return;
         }
         playButton.visible = true;
         playButton.compEnabled = true;
         var roundMetadata:Object=com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverTournamentDetails(param2.tournamentId);
         if(param1 == TournamentState.RUNNING && roundMetadata != null && (roundMetadata.phase == "closing" || (int(roundMetadata.round)>0 && (roundMetadata.played || roundMetadata.bye)))) {
            playButton.componentLabel=this._translator.getText("tournament_wait_round");playButton.compEnabled=false;return;
         }
         if(param1 == TournamentState.PAST)
         {
            playButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PLAY_BUTTON_PAST);
            playButton.compEnabled = false;
         }
         else if(param1 == TournamentState.FUTURE)
         {
            playButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PLAY_BUTTON_FUTURE);
            playButton.compEnabled = false;
         }
         else if(param2.ownRanking != null && param2.ownRanking.eliminated)
         {
            playButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PLAY_BUTTON_ELIMINATED);
            playButton.compEnabled = false;
         }
         else if(param2.hasRounds && param2.ownRanking == null)
         {
            playButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PLAY_BUTTON_NOT_QUALIFIED);
            playButton.compEnabled = false;
         }
         else if(param2.hasRounds && !param2.inRound(this._serverTime.getTime()))
         {
            playButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PLAY_BUTTON_NO_OPEN_ROUND);
            playButton.compEnabled = false;
         }
         else if(param2.ownRanking == null)
         {
            playButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PLAY_BUTTON_REGISTER);
         }
         else if(param2.ownRanking.eliminated)
         {
            playButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PLAY_BUTTON_ELIMINATED);
            playButton.compEnabled = false;
         }
         else
         {
            playButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_PLAY_BUTTON);
         }
      }
      
      private function init() : void
      {
         miniLadderHolder.content = this._miniLadder;
         backButton.componentLabel = this._translator.getText(LangConstants.BACK_BUTTON);
         playButton.visible = false;
         runningTournamentButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_RUNNING_TOURNAMENT_BUTTON);
         pastTournamentButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_PAST_TOURNAMENT_BUTTON);
         futureTournamentButton.componentLabel = this._translator.getText(LangConstants.TOURNAMENT_FUTURE_TOURNAMENT_BUTTON);
         rewardsPresenter.firstThresholdTitle = this._translator.getEnumTranslation(LangConstants.TOURNAMENT_REWARDSPRESENTER_THRESHOLD_ENUM,1);
         rewardsPresenter.secondThresholdTitle = this._translator.getEnumTranslation(LangConstants.TOURNAMENT_REWARDSPRESENTER_THRESHOLD_ENUM,2);
         rewardsPresenter.thirdThresholdTitle = this._translator.getEnumTranslation(LangConstants.TOURNAMENT_REWARDSPRESENTER_THRESHOLD_ENUM,3);
         rewardsPresenter.fourthThresholdTitle = this._translator.getEnumTranslation(LangConstants.TOURNAMENT_REWARDSPRESENTER_THRESHOLD_ENUM,4);
         runningTournamentButton.addEventListener(MouseEvent.CLICK,this.runningTournamentClickHandler);
         pastTournamentButton.addEventListener(MouseEvent.CLICK,this.pastTournamentClickHandler);
         futureTournamentButton.addEventListener(MouseEvent.CLICK,this.futureTournamentClickHandler);
         this._miniLadder.fullLadderButton.addEventListener(MouseEvent.CLICK,this.ladderButtonClickHandler);
         countdown.topField = "";
         countdown.dayField = "";
         countdown.andField = this._translator.getText(LangConstants.TOURNAMENT_COUNTDOWN_AND);
         countdown.timeField = "";
         countdown.bottomField = "";
         helpButton.setTooltip(this._translator.getText(LangConstants.TOURNAMENT_HELP_TOOLTIP));
         runningTournamentMatchesList.list.title = this._translator.getText(LangConstants.TOURNAMENT_MATCHS_LIST_TITLE);
         runningTournamentMatchesList.setTooltip(this._translator.getText(LangConstants.TOURNAMENT_MATCHS_LIST_TOOLTIP));
         tournamentList.list.addEventListener(ItemSelectorList.ITEM_SELECTED,this.tournamentListItemSelectedHandler);
         this._countdown.addEventListener(CountdownModel.COUNT_DOWN_TICK,this.countdownTickHandler);
      }
      
      private function runningTournamentClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new IndexEvent(TOURNAMENT_STATE_CLICKED,TournamentState.RUNNING));
      }
      
      private function pastTournamentClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new IndexEvent(TOURNAMENT_STATE_CLICKED,TournamentState.PAST));
      }
      
      private function futureTournamentClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new IndexEvent(TOURNAMENT_STATE_CLICKED,TournamentState.FUTURE));
      }
      
      private function tournamentListItemSelectedHandler(param1:ItemSelectedEvent) : void
      {
         dispatchEvent(new Index64Event(SELECT_TOURNAMENT,TournamentListItem(param1.item).tournamentId));
      }
      
      private function ladderButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new Event(REQUEST_TOURNAMENT_LADDER));
      }
      
      private function buildTournamentListItems(param1:IMap) : IList
      {
         var _loc4_:TournamentData = null;
         var _loc5_:String = null;
         var _loc6_:TournamentListItem = null;
         var _loc2_:IList = new LinkedList();
         var _loc3_:IIterator = param1.getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            _loc5_ = this._tournamentNameBuilder.computeTournamentName(_loc4_.tournamentType,_loc4_.startTime,_loc4_.endTime);
            _loc6_ = new TournamentListItem(_loc4_.tournamentId,_loc5_);
            _loc2_.addItem(_loc6_);
         }
         return _loc2_;
      }
      
      private function formatTime(param1:Number) : String
      {
         var _loc2_:Date = new Date();
         _loc2_.setTime(param1);
         return this._translator.getText(LangConstants.TIME_FORMAT,StringUtils.twoDigitsNumber(_loc2_.getHours()),StringUtils.twoDigitsNumber(_loc2_.getMinutes()));
      }
      
      private function updateTournamentStateButtons(param1:int, param2:Boolean) : void
      {
         pastTournamentButton.selected = param1 == TournamentState.PAST;
         runningTournamentButton.selected = param1 == TournamentState.RUNNING;
         futureTournamentButton.selected = param1 == TournamentState.FUTURE;
         runningTournamentButton.compEnabled = param2;
      }
   }
}

