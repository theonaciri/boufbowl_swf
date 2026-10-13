package com.ankamagames.boufbowl.client.match
{
   import com.ankamagames.boufbowl.client.facebook.view.FacebookScreenshotMediator;
   import com.ankamagames.boufbowl.client.logging.BoufbowlClientState;
   import com.ankamagames.boufbowl.client.match.controller.ChooseMusicCommand;
   import com.ankamagames.boufbowl.client.match.controller.ComputeMatchPhaseDurationCommand;
   import com.ankamagames.boufbowl.client.match.controller.DisplaySituationCommand;
   import com.ankamagames.boufbowl.client.match.controller.MatchChannelClosedCommand;
   import com.ankamagames.boufbowl.client.match.controller.MatchChannelErrorCommand;
   import com.ankamagames.boufbowl.client.match.controller.MatchEndCommand;
   import com.ankamagames.boufbowl.client.match.controller.PhaseEndCommand;
   import com.ankamagames.boufbowl.client.match.controller.PlayIntroductionCommand;
   import com.ankamagames.boufbowl.client.match.controller.ScriptEndedCommand;
   import com.ankamagames.boufbowl.client.match.controller.StartResolutionCommand;
   import com.ankamagames.boufbowl.client.match.end.view.EndBillboardMediator;
   import com.ankamagames.boufbowl.client.match.end.view.EndBillboardView;
   import com.ankamagames.boufbowl.client.match.model.ChronoModel;
   import com.ankamagames.boufbowl.client.match.model.MatchLaunchDatas;
   import com.ankamagames.boufbowl.client.match.model.MatchModel;
   import com.ankamagames.boufbowl.client.match.resolution.controller.ComputeResolutionCommand;
   import com.ankamagames.boufbowl.client.match.resolution.controller.InitSceneEvent;
   import com.ankamagames.boufbowl.client.match.resolution.view.ResolutionMediator;
   import com.ankamagames.boufbowl.client.match.strategic.view.scorepanel.ScorePanelMediator;
   import com.ankamagames.boufbowl.client.match.view.MatchMediator;
   import com.ankamagames.boufbowl.client.match.view.MatchView;
   import com.ankamagames.boufbowl.client.match.view.WaitingScreenView;
   import com.ankamagames.boufbowl.client.network.LobbyMessageHandler;
   import com.ankamagames.xgaming.utils.display.stage.IStageWrapper;
   import com.ankamagames.xgaming.utils.injection.AbstractContextPart;
   import com.ankamagames.xgaming.utils.shortcut.IShortcutManager;
   import com.ankamagames.xgaming.utils.shortcut.KeyboardShortcut;
   import com.ankamagames.xgaming.utils.shortcut.ShortcutManager;
   import flash.events.KeyboardEvent;
   import flash.ui.Keyboard;
   
   public class MatchContextPart extends AbstractContextPart
   {
      
      public function MatchContextPart()
      {
         super();
      }
      
      override protected function configure() : void
      {
         moduleCommandMap.mapEvent(MatchMessageHandler.MATCH_END,MatchEndCommand);
         moduleCommandMap.mapEvent(MatchMessageHandler.RESOLUTION_SCENARIO,StartResolutionCommand);
         commandMap.mapEvent(MatchModel.STATE_CHANGED,ComputeMatchPhaseDurationCommand);
         commandMap.mapEvent(MatchModel.STATE_CHANGED,ChooseMusicCommand);
         if(!MatchLaunchDatas(injector.getInstance(MatchLaunchDatas)).spectatorMode)
         {
            commandMap.mapEvent(ScorePanelMediator.GONG_CLICKED,PhaseEndCommand);
            commandMap.mapEvent(ChronoModel.END,PhaseEndCommand);
            moduleCommandMap.mapEvent(DisplaySituationCommand.CONCEDE_TOUCHDOWN,PhaseEndCommand);
         }
         commandMap.mapEvent(ResolutionMediator.SCRIPT_ENDED,ScriptEndedCommand);
         commandMap.mapEvent(MatchModule.PLAY_INTRODUCTION,PlayIntroductionCommand);
         commandMap.mapEvent(InitSceneEvent.EVENT,ComputeResolutionCommand);
         moduleCommandMap.mapEvent(MatchMessageHandler.CHANNEL_CLOSED,MatchChannelClosedCommand);
         moduleCommandMap.mapEvent(MatchMessageHandler.CHANNEL_ERROR,MatchChannelErrorCommand);
         moduleCommandMap.mapEvent(LobbyMessageHandler.CHANNEL_CLOSED,MatchChannelErrorCommand);
         moduleCommandMap.mapEvent(LobbyMessageHandler.CHANNEL_ERROR,MatchChannelErrorCommand);
         injector.mapSingleton(BoufbowlClientState);
         injector.mapSingletonOf(IMatchColorScheme,MatchColorScheme);
         injector.mapSingleton(MatchView);
         mediatorMap.mapView(MatchView,MatchMediator);
         injector.mapSingleton(EndBillboardView);
         mediatorMap.mapView(EndBillboardView,EndBillboardMediator);
         injector.mapSingleton(WaitingScreenView);
         this.configureShortcuts();
      }
      
      private function configureShortcuts() : void
      {
         injector.mapSingletonOf(IShortcutManager,ShortcutManager);
         var _loc1_:IShortcutManager = injector.getInstance(IShortcutManager);
         _loc1_.initialize(IStageWrapper(injector.getInstance(IStageWrapper)).stage,moduleDispatcher);
         _loc1_.addShortcut(new KeyboardShortcut(KeyboardEvent.KEY_DOWN,Keyboard.F12,FacebookScreenshotMediator.TAKE_SCREENSHOT));
      }
   }
}

