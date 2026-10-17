package com.ankamagames.boufbowl.client.application.controller
{
   import as3.collections.ArrayList;
   import as3.collections.LinkedMap;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.client.application.ApplicationContext;
   import com.ankamagames.boufbowl.client.application.BoufbowlViewDisplayer;
   import com.ankamagames.boufbowl.client.application.BoufbowlViews;
   import com.ankamagames.boufbowl.client.application.IBoufbowlViewDisplayer;
   import com.ankamagames.boufbowl.client.application.flashvars.FlashVars;
   import com.ankamagames.boufbowl.client.application.messagebox.event.MessageBoxEvent;
   import com.ankamagames.boufbowl.client.boufbowler.model.ClassAttributesModel;
   import com.ankamagames.boufbowl.client.club.model.ClubBoufbowlerFactory;
   import com.ankamagames.boufbowl.client.club.model.ClubBoufbowlerModel;
   import com.ankamagames.boufbowl.client.club.model.ClubInformation;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.login.model.AccountInformations;
   import com.ankamagames.boufbowl.client.match.strategic.model.BoufbowlerAttributesModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IClubBoufbowlerModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.RulesConstants;
   import com.ankamagames.boufbowl.client.matchmaking.model.MatchCreationModel;
   import com.ankamagames.boufbowl.client.network.LobbyMessageHandler;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.PremiumContentModel;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.BoufbowlerPaletteItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.ClubPaletteItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.SigilBackgroundItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.SigilChargeItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.StadiumItem;
   import com.ankamagames.boufbowl.client.premiumservice.common.model.item.UniqueCharacterItem;
   import com.ankamagames.boufbowl.client.proto.Converters;
   import com.ankamagames.boufbowl.protocol.CustomisationSessionAcceptedMessage;
   import com.ankamagames.boufbowl.protocol.LadderDataMessage;
   import com.ankamagames.boufbowl.protocol.LadderRow;
   import com.ankamagames.boufbowl.protocol.League;
   import com.ankamagames.boufbowl.protocol.OutstandingTournamentsMessage;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.flashvars.FlashVarsManager;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.protocol.NetworkEventDispatcher;
   import com.ankamagames.xgaming.utils.protocol.NetworkMessageEvent;
   import com.netease.protobuf.Int64;
   import com.netease.protobuf.Message;
   import com.netease.protobuf.UInt64;
   import flash.display.Sprite;
   import flash.display.Stage;
   import flash.events.MouseEvent;
   import flash.utils.getDefinitionByName;
   import flash.text.TextField;
   import flash.text.TextFormat;
   import flash.utils.getQualifiedClassName;
   import flash.utils.setTimeout;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class StartUpApplicationCommand extends ModuleCommand
   {
      
      private static var app:ApplicationContext;
      
      private static var teams:ArrayList;
      
      private static var toolbar:Sprite;
      
      public static const AUTO_CONNECT:String = "com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.AUTO_CONNECT";
      
      public static const TUTORIAL_FLASHVAR_EXPECTED_VALUE:String = "1";
      
      private var vars:FlashVarsManager;
      
      public function StartUpApplicationCommand()
      {
         super();
      }
      
      private static function displayer() : IBoufbowlViewDisplayer
      {
         return app.contextInjector.getInstance(IBoufbowlViewDisplayer);
      }
      
      public static function showHome() : void
      {
         app.hideMessageBox();
         BoufbowlViewDisplayer(displayer()).displayView(BoufbowlViews.MATCHMAKING,true);
      }
      
      public static function showTeams() : void
      {
         app.hideMessageBox();
         ClubModel(app.contextInjector.getInstance(ClubModel)).predefinedClubs = teams;
         displayer().displayPredefinedClubSelection();
      }
      
      public static function teamName(id:UInt64) : String
      {
         if(id == null)
         {
            return "";
         }
         var i:int = 0;
         while(i < teams.numItems)
         {
            var team:ClubModel = teams.getItemAt(i);
            if(team.clubInformation.id.low == id.low && team.clubInformation.id.high == id.high)
            {
               return team.clubInformation.name;
            }
            i++;
         }
         return "Offline team";
      }
      
      public static function offlineRequest(request:Object) : void
      {
         if(app == null)
         {
            return;
         }
         setTimeout(function():void
         {
            handleRequest(request);
         },50);
      }
      
      private static function emit(type:String, cls:Class, message:Message) : void
      {
         var dispatcher:NetworkEventDispatcher = app.contextInjector.getInstance(NetworkEventDispatcher,"LOBBY");
         dispatcher.toModules(new NetworkMessageEvent(type,cls,message));
      }
      
      private static function handleRequest(request:Object) : void
      {
         var name:String = getQualifiedClassName(request).split("::").pop();
         app.hideMessageBox();
         if(name == "CustomisationSessionRequestMessage")
         {
            var session:CustomisationSessionAcceptedMessage = new CustomisationSessionAcceptedMessage();
            session.customisationType = request.type;
            if(request.hasBoufbowlerId)
            {
               session.boufbowlerId = request.boufbowlerId;
            }
            displayer().displayPremiumService(session.customisationType);
            emit(LobbyMessageHandler.CUSTOMISATION_SESSION_ACCEPTED,CustomisationSessionAcceptedMessage,session);
         }
         else if(name == "LadderByNickRequestMessage" || name == "LadderByLeagueRequestMessage")
         {
            var ladder:LadderDataMessage = new LadderDataMessage();
            ladder.ownData = new LadderRow();
            ladder.league = League.LEAGUE_CRAQUELEUR;
            ladder.subLeague = 1;
            emit(LobbyMessageHandler.LADDER_DATA,LadderDataMessage,ladder);
         }
         else if(name == "OutstandingTournamentsRequestMessage")
         {
            var tournaments:OutstandingTournamentsMessage = new OutstandingTournamentsMessage();
            tournaments.currentTime = new Date().time;
            emit(LobbyMessageHandler.OUTSTANDING_TOURNAMENTS,OutstandingTournamentsMessage,tournaments);
         }
         else if(name == "PredefinedClubSelectionMessage")
         {
            var current:ClubModel = app.contextInjector.getInstance(ClubModel);
            var i:int = 0;
            while(i < teams.numItems)
            {
               var team:ClubModel = teams.getItemAt(i);
               if(team.clubInformation.id.low == request.clubId.low && team.clubInformation.id.high == request.clubId.high)
               {
                  var info:ClubInformation = new ClubInformation(team.clubInformation.id,request.clubName,request.sigilBackground,request.sigilCharge,request.paletteId,Converters.toColor3(request.firstColor),Converters.toColor3(request.secondColor),Converters.toColor3(request.patternColor));
                  var roster:LinkedMap = new LinkedMap();
                  var factory:ClubBoufbowlerFactory = app.contextInjector.getInstance(ClubBoufbowlerFactory);
                  for each(var player:IClubBoufbowlerModel in team.boufbowlers.toArray())
                  {
                     roster.addItem(player.id,factory.teamColorizedBoufbowler(player,info.mainColor));
                  }
                  current.setup(info,roster,false);
                  break;
               }
               i++;
            }
            showHome();
         }
         else if(name == "MatchRequestMessage")
         {
            MatchCreationModel(app.contextInjector.getInstance(MatchCreationModel)).matchRequestRunning = false;
            var dispatcher:NetworkEventDispatcher = app.contextInjector.getInstance(NetworkEventDispatcher,"LOBBY");
            dispatcher.toModules(MessageBoxEvent.infos("Offline preview: online matches need a game server. You can play the tutorial from Home.","OK"));
         }
         else
         {
            PremiumContentModel(app.contextInjector.getInstance(PremiumContentModel)).refreshRequestRunning = false;
         }
      }
      
      private static function createToolbar() : void
      {
         toolbar = new Sprite();
         toolbar.x = 620;
         toolbar.y = 0;
         toolbar.graphics.beginFill(2106667,0.95);
         toolbar.graphics.drawRect(0,0,348,26);
         toolbar.graphics.endFill();
         addButton("Offline",8,60,null);
         addButton("Home",76,55,function():void
         {
            showHome();
         });
         addButton("Teams",139,60,function():void
         {
            showTeams();
         });
         addButton("Tutorial",207,70,function():void
         {
            app.hideMessageBox();
            displayer().displayTutorial();
         });
         addButton("Quit",285,50,function():void
         {
            Object(getDefinitionByName("flash.desktop.NativeApplication")).nativeApplication.exit();
         });
         Stage(app.contextInjector.getInstance(Stage)).addChild(toolbar);
      }
      
      private static function addButton(label:String, xPos:int, width:int, callback:Function) : void
      {
         var text:TextField;
         var button:Sprite = new Sprite();
         button.x = xPos;
         button.graphics.beginFill(callback == null ? 2106667 : 4608348);
         button.graphics.drawRect(0,2,width,22);
         button.graphics.endFill();
         text = new TextField();
         text.defaultTextFormat = new TextFormat("_sans",12,16777215);
         text.text = label;
         text.width = width;
         text.height = 24;
         text.selectable = false;
         text.mouseEnabled = false;
         button.addChild(text);
         if(callback != null)
         {
            button.buttonMode = true;
            button.addEventListener(MouseEvent.CLICK,function(event:MouseEvent):void
            {
               callback();
            });
         }
         toolbar.addChild(button);
      }
      
      override public function execute() : void
      {
         var diagnostic:TextField;
         try
         {
            app = injector.getInstance(ApplicationContext);
            vars = injector.getInstance(FlashVarsManager);
            seedData();
            if(vars.getValue(FlashVars.TUTORIAL) == "1")
            {
               displayer().displayTutorial();
            }
            else
            {
               showHome();
            }
            createToolbar();
         }
         catch(error:Error)
         {
            diagnostic = new TextField();
            diagnostic.defaultTextFormat = new TextFormat("_sans",16,16737894);
            diagnostic.text = error.toString();
            diagnostic.wordWrap = true;
            diagnostic.multiline = true;
            diagnostic.width = 1024;
            diagnostic.height = 500;
            Stage(injector.getInstance(Stage)).addChild(diagnostic);
         }
      }
      
      private function seedData() : void
      {
         var account:AccountInformations = injector.getInstance(AccountInformations);
         account.nickname = "Offline Player";
         account.lang = vars.getValue(FlashVars.LANGUAGE);
         var premium:PremiumContentModel = injector.getInstance(PremiumContentModel);
         var colors:Array = [Color3.fromRgbUInt(3504335),Color3.fromRgbUInt(14922564),Color3.fromRgbUInt(13652048),Color3.fromRgbUInt(7842128),Color3.WHITE,Color3.BLACK];
         var hair:Array = [Color3.fromRgbUInt(16750592),Color3.fromRgbUInt(16113040),Color3.fromRgbUInt(6240286),Color3.BLACK];
         var skin:Array = [Color3.fromRgbUInt(16766381),Color3.fromRgbUInt(14195307),Color3.fromRgbUInt(9527099)];
         var eyes:Array = [Color3.fromRgbUInt(6723891),Color3.fromRgbUInt(4487099),Color3.BLACK];
         var palettes:LinkedMap = new LinkedMap();
         var clubPalettes:LinkedMap = new LinkedMap();
         var backgrounds:LinkedMap = new LinkedMap();
         var charges:LinkedMap = new LinkedMap();
         var stadiums:LinkedMap = new LinkedMap();
         var uniqueCharacters:LinkedMap = new LinkedMap();
         var heroes:Array = [[501,10,1,15],[502,9,2,16],[503,10,2,17],[504,12,1,18],[505,6,1,19],[506,11,2,20],[507,2,2,21],[508,1,2,22],[509,4,1,23],[510,3,2,24],[511,7,1,25],[512,3,1,26],[513,13,1,27],[514,8,1,28],[515,5,1,34],[516,12,1,35],[517,11,1,36],[518,14,1,37]];
         var attributes:Map = new Map();
         var i:int = 1;
         while(i <= 14)
         {
            palettes.addItem(i,new BoufbowlerPaletteItem(1,0,i,i,0,hair,eyes,skin));
            attributes.addItem(i,new ClassAttributesModel(i,1 + i % 4,new BoufbowlerAttributesModel(12,10,10,10,16,3)));
            i++;
         }
         clubPalettes.addItem(1,new ClubPaletteItem(1,0,1,colors,colors,colors));
         for each(var hero:Array in heroes)
         {
            uniqueCharacters.addItem(hero[0],new UniqueCharacterItem(2,0,hero[0],hero[1],hero[2]));
            palettes.addItem(hero[3],new BoufbowlerPaletteItem(2,0,hero[3],0,hero[0],hair,eyes,skin));
         }
         i = 1;
         while(i <= 9)
         {
            stadiums.addItem(i,new StadiumItem(1,0,i));
            i++;
         }
         i = 1;
         // All embedded heraldry: 32 backgrounds, 27 charges.
         for(i=1;i<=32;i++) backgrounds.addItem(i,new SigilBackgroundItem(1,0,i));
         for(i=1;i<=27;i++) charges.addItem(i,new SigilChargeItem(1,0,i));
         premium.updateCustomisationAssetsLists(stadiums,uniqueCharacters,clubPalettes,palettes,backgrounds,charges);
         premium.updateCustomisationCredits(10,10,10,10);
         premium.updateTournamentTickets(0);
         var rules:RulesConstants = injector.getInstance(RulesConstants);
         rules.classAttributes = attributes;
         rules.maxBoufbowlerCountPerRole = 5;
         i = 1;
         while(i <= 9)
         {
            rules.setMaxTurnDuration(i,24);
            rules.setPeriodTurnDuration(i,12);
            rules.setClassOrderUseByMatch(i,1);
            i++;
         }
         teams = new ArrayList();
         var playerNames:Array = ["Aria","Baff","Cora","Dara","Elia","Fara","Gust","Hana","Iris","Jora"];
         // Open with the five tutorial class/gender combinations, followed by five distinct classes.
         var starterRoster:Array = [[1,1],[1,2],[4,2],[3,2],[6,1],[2,1],[5,2],[7,1],[8,2],[10,1]];
         var teamNames:Array = ["Offline Bonta","Offline Brakmar","Offline Amakna"];
         var teamIndex:int = 0;
         while(teamIndex < 3)
         {
            var roster:LinkedMap = new LinkedMap();
            i = 0;
            while(i < 10)
            {
               var cls:int = teamIndex == 0 ? starterRoster[i][0] : 1 + (i + teamIndex * 3) % 14;
               var gender:int = teamIndex == 0 ? starterRoster[i][1] : 1 + i % 2;
               var id:Int64 = new Int64(1 + i);
               roster.addItem(id,new ClubBoufbowlerModel(id,playerNames[i],cls,gender,0,1 + cls % 4,cls,1,hair[0],skin[0],eyes[0],colors[teamIndex],new BoufbowlerAttributesModel(12,10,10,10,16,3)));
               i++;
            }
            var info:ClubInformation = new ClubInformation(new UInt64(teamIndex + 1),teamNames[teamIndex],1,1,1,colors[teamIndex],Color3.WHITE,colors[teamIndex]);
            var team:ClubModel = new ClubModel();
            team.setup(info,roster,false);
            teams.addItem(team);
            teamIndex++;
         }
         var current:ClubModel = injector.getInstance(ClubModel);
         var translator:ITranslator = injector.getInstance(ITranslator);
         var galleryIndex:int = 0;
         while(galleryIndex < 2)
         {
            var galleryRoster:LinkedMap = new LinkedMap();
            i = 0;
            while(i < 10)
            {
               var heroIndex:int = galleryIndex * 10 + i;
               var galleryId:Int64 = new Int64(i + 1);
               if(heroIndex < heroes.length)
               {
                  hero = heroes[heroIndex];
                  galleryRoster.addItem(galleryId,new ClubBoufbowlerModel(galleryId,translator.getEnumTranslation(LangConstants.UNIQUE_CHARACTER_NAME_ENUM,hero[0]),hero[1],hero[2],hero[0],1 + hero[1] % 4,hero[3],2,hair[0],skin[0],eyes[0],colors[galleryIndex],new BoufbowlerAttributesModel(12,10,10,10,16,3)));
               }
               else
               {
                  galleryRoster.addItem(galleryId,new ClubBoufbowlerModel(galleryId,playerNames[i],i + 1,1,0,1 + (i + 1) % 4,i + 1,1,hair[0],skin[0],eyes[0],colors[galleryIndex],new BoufbowlerAttributesModel(12,10,10,10,16,3)));
               }
               i++;
            }
            var gallery:ClubModel = new ClubModel();
            gallery.setup(new ClubInformation(new UInt64(galleryIndex + 4),galleryIndex == 0 ? "Offline Legends" : "Offline Heroes",1,1,1,colors[galleryIndex],Color3.WHITE,colors[galleryIndex]),galleryRoster,false);
            teams.addItem(gallery);
            galleryIndex++;
         }
         var first:ClubModel = teams.getItemAt(0);
         current.setup(first.clubInformation,first.boufbowlers,false);
         current.predefinedClubs = teams;
      }
   }
}

