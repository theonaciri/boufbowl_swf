package com.ankamagames.boufbowl.client.matchmaking.view
{
   import as3.collections.ILinkedMap;
   import as3.collections.IMap;
   import as3.collections.LinkedMap;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.components.matchcreation.MatchCreationUI;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.StadiumItem;
   import com.ankamagames.boufbowl.config.IStadiumsConfig;
   import com.ankamagames.boufbowl.config.StadiumSpecificData;
   import com.ankamagames.boufbowl.ui.components.matchcreation.stadium.StadiumSelector;
   import com.ankamagames.boufbowl.ui.components.matchcreation.stadium.StadiumPreviewWithAvailability;
   import com.ankamagames.boufbowl.ui.components.matchcreation.stadium.StadiumViewData;
   import com.ankamagames.xgaming.utils.event.IndexEvent;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.reider.log4AS3.ILogger;
   import flash.events.MouseEvent;
   import flash.events.Event;
   import flash.display.Sprite;
   import flash.display.Stage;
   import flash.text.TextField;
   import flash.text.TextFormat;
   import flash.filters.GlowFilter;
   import flash.geom.Rectangle;
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   
   public class MatchCreationView extends MatchCreationUI
   {
      
      public static const STADIUM_CLICKED:String = "com.ankamagames.boufbowl.client.matchmaking.view.MatchCreationView.STADIUM_CLICKED";
      
      private static const STADIUM_DESC_HEIGHT:Number = 180;
      
      private static const LOGGER:ILogger = LoggerFactory.getLogger(MatchCreationView);
      
      private var _stadiumsConfig:IStadiumsConfig;
      
      private var _translator:ITranslator;
      
      private var _stadiumDescriptionTextBuilder:StadiumDescriptionTextBuilder;
      
      private var _pageClub:String;
      private var _pageStadium:int;
      private var _pageTeam:TextField;
      private var _pageStatus:TextField;
      private var _pageRandom:Sprite;
      private var _pageRandomWaiting:TextField;
      private var _pageCpu:Sprite;
      private var _pageCancel:Sprite;
      private var _pageStage:Stage;
      private var _pageChallenge:Boolean;
      private var _pageWaitingBadges:Array;

      public function MatchCreationView(param1:IStadiumsConfig, param2:ITranslator, param3:StadiumDescriptionTextBuilder)
      {
         super();
         this._stadiumsConfig = param1;
         this._translator = param2;
         this._stadiumDescriptionTextBuilder = param3;
         this.init();
         this.initTexts();
         if(StartUpApplicationCommand.serverMode()) this.initServerPage();
      }
      
      internal function updateStadiums(param1:ILinkedMap) : void
      {
         this.fillStadiumsList(param1);
         if(StartUpApplicationCommand.serverMode()) this.refreshStadiumWaiting(StartUpApplicationCommand.serverMatchPageInfo());
      }
      
      internal function selectStadium(param1:int) : void
      {
         if(!StartUpApplicationCommand.serverMode()) { this.selectChallengeStadium(param1);return; }
         this._pageStadium=param1 > 0 ? param1 : 0;
         var enabled:Array=StartUpApplicationCommand.serverMatchPageInfo().stadiums;
         if(enabled.indexOf(this._pageStadium) < 0) this._pageStadium=0;
         tabs.randomTab.stadiumsSelector.selectedStadium=this._pageStadium;
         tabs.challengeTab.stadiumSelector.selectedStadium=this._pageStadium;
         var description:String=this._pageStadium == 0 ? "<span fontWeight=\"bold\">Stade aléatoire</span><br />Le stade sera choisi parmi les terrains disponibles." : "<span fontWeight=\"bold\">"+this._translator.getEnumTranslation(LangConstants.STADIUM_NAME_ENUM,this._pageStadium)+"</span><br />Ce terrain sera utilisé pour votre match.";
         tabs.randomTab.descriptionTextZone.setContent(description);
         tabs.challengeTab.descriptionTextZone.setContent(description);
         var rules:String=this._pageStadium > 0 ? this._stadiumDescriptionTextBuilder.buildDescription(this._pageStadium) : "Chaque stade possède ses propres règles. Touchez sa miniature pour le choisir.";
         tabs.randomTab.rulesTextZone.setContent(rules);
         tabs.challengeTab.rulesTextZone.setContent(rules);
         if(this._pageRandom != null) this._pageRandom.filters=this._pageStadium == 0 ? [new GlowFilter(0x79963a,.6,4,4,2)] : [];
      }
      
      private function init() : void
      {
         tabs.randomTab.allStadiumsButton.visible = false;
         tabs.randomTab.fastMatchButton.visible = false;
         tabs.randomTab.championshipButton.visible = false;
         tabs.randomTab.buyStadiumsButton.visible = false;
         tabs.challengeTab.buyStadiumsButton.visible = false;
         tabs.randomTab.playButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_PLAY_BUTTON);
         tabs.challengeTab.playButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_PLAY_BUTTON);
         tabs.randomTabButton.addEventListener(MouseEvent.CLICK,this.randomTabButtonClickHandler);
         tabs.challengeTabButton.addEventListener(MouseEvent.CLICK,this.challengeTabButtonClickHandler);
         tabs.randomTab.stadiumsSelector.addEventListener(StadiumSelector.STADIUM_ROLLED_OVER,this.randomMatchStadiumRolledOverHandler);
         tabs.challengeTab.stadiumSelector.addEventListener(StadiumSelector.STADIUM_CLICKED,this.friendlyMatchStadiumClickedHandler);
      }
      
      private function pageText(text:String,x:int,y:int,width:int,height:int=28,bold:Boolean=false) : TextField
      {
         var label:TextField=new TextField();
         label.defaultTextFormat=new TextFormat("Verdana",12,0x463d2b,bold);
         label.embedFonts=true;label.antiAliasType="advanced";
         label.text=text;label.x=x;label.y=y;label.width=width;label.height=height;
         label.wordWrap=true;label.selectable=false;label.mouseEnabled=false;
         addChild(label);return label;
      }

      private function pageButton(text:String,x:int,y:int,callback:Function) : Sprite
      {
         return StartUpApplicationCommand.serverMatchPageButton(this,text,x,y,190,callback);
      }

      private function initServerPage() : void
      {
         tabs.randomTabButton.componentLabel="Trouver un match";
         tabs.challengeTabButton.componentLabel="Défier un joueur";
         tabs.randomTab.title="Touchez un stade pour le choisir, ou gardez le tirage au sort.";
         tabs.randomTab.stadiumsSelector.selectableStadiums=true;
         tabs.randomTab.stadiumsSelector.addEventListener(StadiumSelector.STADIUM_CLICKED,this.friendlyMatchStadiumClickedHandler);
         tabs.challengeTab.explain="";
         tabs.challengeTab.opponentExplain="Pseudo exact du joueur à inviter";
         tabs.challengeTab.playButton.componentLabel="DÉFIER";
         tabs.randomTab.playButton.componentLabel="JOUER";
         tabs.randomTab.descriptionTextZone.defaultFontSize=12;
         tabs.randomTab.rulesTextZone.defaultFontSize=12;
         tabs.challengeTab.descriptionTextZone.defaultFontSize=12;
         tabs.challengeTab.rulesTextZone.defaultFontSize=12;
         pageText("VOTRE ÉQUIPE",34,218,190,24,true);
         this._pageTeam=pageText("",34,245,190,42);
         pageButton("Changer d’équipe",34,290,this.nextServerTeam);
         this._pageRandom=pageButton("Stade aléatoire",34,332,this.randomServerStadium);
         this._pageRandomWaiting=pageText("— en attente",34,365,190,20);
         this._pageCpu=pageButton("Contre l’ordinateur",34,392,function():void { thisPage.submitServerMatch("cpu_match"); });
         this._pageCancel=pageButton("Annuler la recherche",34,434,function():void { thisPage.submitServerMatch("queue_leave"); });
         var thisPage:MatchCreationView=this;
         if(StartUpApplicationCommand.serverMatchPageInfo().tournament)
            pageButton("Rejoindre un tournoi",34,477,function():void { thisPage.submitServerMatch("tournament_match"); });
         pageButton("Joueurs et amis",34,519,function():void { StartUpApplicationCommand.serverMatchPageCommunity(); });
         this._pageStatus=pageText("",650,504,320,55);
         this.initWaitingBadges();
         addEventListener(Event.ADDED_TO_STAGE,this.serverPageAdded);
         addEventListener(Event.REMOVED_FROM_STAGE,this.serverPageRemoved);
         this.refreshServerPage();
         this.selectStadium(0);
      }

      private function initWaitingBadges() : void
      {
         this._pageWaitingBadges=[];
         var selectors:Array=[tabs.randomTab.stadiumsSelector,tabs.challengeTab.stadiumSelector];
         for(var tab:int=0;tab<selectors.length;tab++)
         {
            for(var index:int=0;index<12;index++)
            {
               var badge:Sprite=new Sprite();
               badge.mouseEnabled=false;badge.mouseChildren=false;
               var label:TextField=pageText("",0,-1,108,19);
               var format:TextFormat=new TextFormat("Verdana",10,0xffffff,false);
               format.align="center";label.defaultTextFormat=format;
               badge.addChild(label);addChild(badge);
               this._pageWaitingBadges.push({selector:selectors[tab],index:index,challenge:tab == 1,badge:badge,label:label});
            }
         }
      }

      private function refreshStadiumWaiting(state:Object) : void
      {
         if(this._pageWaitingBadges == null) return;
         for each(var entry:Object in this._pageWaitingBadges)
         {
            var preview:StadiumPreviewWithAvailability=entry.selector.getStadium(entry.index);
            var id:int=preview.stadiumId;
            var badge:Sprite=entry.badge;
            badge.visible=entry.challenge == this._pageChallenge && preview.visible && state.stadiums.indexOf(id) >= 0;
            if(!badge.visible) continue;
            var known:Boolean=state.waiting_by_stadium != null && state.waiting_by_stadium.hasOwnProperty(String(id));
            var count:int=known ? int(state.waiting_by_stadium[String(id)]) : 0;
            var bounds:Rectangle=preview.getBounds(this);
            var width:Number=Math.max(70,Math.min(108,bounds.width-4));
            badge.x=bounds.x+(bounds.width-width)/2;
            badge.y=bounds.bottom-19;
            badge.graphics.clear();badge.graphics.beginFill(count > 0 ? 0x365b2a : 0x343a33,.95);
            badge.graphics.drawRoundRect(0,0,width,17,4);badge.graphics.endFill();
            entry.label.width=width;
            entry.label.text=(known ? String(count) : "—")+" en attente";
         }
      }

      private function serverPageAdded(event:Event) : void
      {
         this._pageStage=stage;
         this._pageStage.addEventListener("restorationMatchmakingUpdated",this.refreshServerPage,false,0,true);
         this.refreshServerPage();
      }

      private function serverPageRemoved(event:Event) : void
      {
         if(this._pageStage != null) this._pageStage.removeEventListener("restorationMatchmakingUpdated",this.refreshServerPage);
         this._pageStage=null;
      }

      private function refreshServerPage(event:Event=null) : void
      {
         var state:Object=StartUpApplicationCommand.serverMatchPageInfo();
         if(this._pageClub == null) this._pageClub=String(state.club_id);
         for each(var team:Object in state.clubs)
            if(team.id == this._pageClub) this._pageTeam.text=team.name;
         this._pageCancel.visible=Boolean(state.waiting);
         var randomCount:int=state.waiting_opponents == null ? 0 : int(state.waiting_opponents);
         this._pageRandomWaiting.text=state.waiting_opponents == null ? "— en attente" : String(randomCount)+(randomCount == 1 ? " joueur en attente" : " joueurs en attente");
         this._pageRandomWaiting.textColor=randomCount > 0 ? 0x365b2a : 0x463d2b;
         this._pageStatus.text=state.waiting ? "Recherche d’un adversaire en cours… Vous pouvez l’annuler à gauche." : "Autres joueurs en recherche de match libre. Un joueur peut apparaître sur plusieurs stades.";
         this.refreshStadiumWaiting(state);
         tabs.randomTab.playButton.compEnabled=!state.waiting;
         if(state.club != null)
         {
            clubCard.teamName=state.club.name;
            clubCard.blason.update(state.club.sigilCharge,state.club.sigilBackground);
            clubCard.blason.updateColors(state.club.mainColor,state.club.alternateColor,state.club.sigilColor);
         }
      }

      private function nextServerTeam() : void
      {
         var clubs:Array=StartUpApplicationCommand.serverMatchPageInfo().clubs;
         if(clubs.length == 0) return;
         var index:int=0;
         for(var i:int=0;i<clubs.length;i++) if(clubs[i].id == this._pageClub) index=(i+1)%clubs.length;
         this._pageClub=clubs[index].id;
         StartUpApplicationCommand.serverMatchPageRequest("select_club",this._pageClub);
         this.refreshServerPage();
      }

      private function randomServerStadium() : void
      {
         dispatchEvent(new IndexEvent(STADIUM_CLICKED,0));
      }

      internal function serverPageMode(challenge:Boolean) : void
      {
         if(!StartUpApplicationCommand.serverMode()) return;
         this._pageChallenge=challenge;
         this._pageCpu.visible=!challenge;
         this.refreshStadiumWaiting(StartUpApplicationCommand.serverMatchPageInfo());
      }

      internal function submitServerMatch(operation:String) : void
      {
         if(StartUpApplicationCommand.serverMatchPageRequest(operation,this._pageClub,this._pageStadium,tabs.challengeTab.opponentName))
            this._pageStatus.text=operation == "queue_leave" ? "Annulation envoyée…" : operation == "challenge" ? "Défi envoyé. En attente de la réponse du joueur." : "Demande envoyée…";
      }

      private function initTexts() : void
      {
         backButtonSprite.componentLabel = this._translator.getText(LangConstants.BACK_BUTTON);
         tabs.randomTabButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_RANDOM_TAB);
         tabs.challengeTabButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_FRIENDLY_TAB);
         tabs.randomTab.allStadiumsButton.componentLabel = this._translator.getText(LangConstants.MATCHMAKING_STADIUM_SELECT_ALL_BUTTON);
         tabs.randomTab.title = this._translator.getText(LangConstants.MATCHMAKING_STADIUMEXPLORATOR_TITLE);
         tabs.challengeTab.opponentLabel = this._translator.getText(LangConstants.MATCHMAKING_OPPONENT_LABEL);
         tabs.challengeTab.explain = this._translator.getText(LangConstants.MATCHMAKING_MATCHCREATION_CHALLENGE_EXPLANATION);
         tabs.challengeTab.opponentExplain = this._translator.getText(LangConstants.MATCHMAKING_OPPONENT_EXPLAIN);
         tabs.randomTab.descriptionTextZone.setContent("");
         tabs.randomTab.rulesTextZone.setContent("");
      }
      
      private function fillStadiumsList(param1:ILinkedMap) : void
      {
         var _loc4_:StadiumItem = null;
         var _loc5_:StadiumSpecificData = null;
         var _loc2_:IMap = new LinkedMap();
         var _loc3_:IIterator = param1.getIterator();
         var enabled:Array=StartUpApplicationCommand.serverMode() ? StartUpApplicationCommand.serverMatchPageInfo().stadiums : null;
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            if(enabled != null && enabled.indexOf(_loc4_.stadium) < 0) continue;
            _loc5_ = this._stadiumsConfig.getStadiumData(_loc4_.stadium);
            if(_loc5_ == null)
            {
               LOGGER.warn("No StadiumSpecificData found for stadium {}",_loc4_.stadium);
            }
            else
            {
               _loc2_.addItem(_loc4_.stadium,new StadiumViewData(_loc4_.availability));
            }
         }
         tabs.challengeTab.stadiumSelector.setup(_loc2_);
         tabs.randomTab.stadiumsSelector.setup(_loc2_);
      }
      
      private function selectChallengeStadium(param1:int) : void
      {
         tabs.challengeTab.stadiumSelector.selectedStadium = param1;
         tabs.challengeTab.descriptionTextZone.setContent(param1 > 0 ? "<span fontWeight=\"bold\">" + this._translator.getEnumTranslation(LangConstants.STADIUM_NAME_ENUM,param1) + "</span><br /><br />" + this._translator.getEnumTranslation(LangConstants.STADIUM_DESCRIPTION_ENUM,param1) : "");
         tabs.challengeTab.rulesTextZone.setContent(param1 > 0 ? this._stadiumDescriptionTextBuilder.buildDescription(param1) : "");
      }
      
      private function randomMatchStadiumRolledOverHandler(param1:IndexEvent) : void
      {
         if(StartUpApplicationCommand.serverMode()) return;
         tabs.randomTab.descriptionTextZone.setContent("<span fontWeight=\"bold\">" + this._translator.getEnumTranslation(LangConstants.STADIUM_NAME_ENUM,param1.index) + "</span><br /><br />" + this._translator.getEnumTranslation(LangConstants.STADIUM_DESCRIPTION_ENUM,param1.index));
         tabs.randomTab.rulesTextZone.setContent(this._stadiumDescriptionTextBuilder.buildDescription(param1.index));
      }
      
      private function friendlyMatchStadiumClickedHandler(param1:IndexEvent) : void
      {
         dispatchEvent(new IndexEvent(STADIUM_CLICKED,param1.index));
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.MATCHMAKING_STADIUMSELECTOR_CLICKED));
      }
      
      private function challengeTabButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.MATCHMAKING_TABBUTTON_CLICKED));
      }
      
      private function randomTabButtonClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.MATCHMAKING_TABBUTTON_CLICKED));
      }
      
   }
}

