package com.ankamagames.boufbowl.client.tutorial.controller
{
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.client.application.BoufbowlViews;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.login.model.AccountInformations;
   import com.ankamagames.xgaming.audio.controller.IAudioController;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.injection.module.event.DisplayViewEvent;
   import flash.events.Event;
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   import flash.net.URLRequest;
   import flash.net.navigateToURL;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class TutorialFinishedCommand extends ModuleCommand
   {
      
      public static const TARGET_WINDOW:String = "_top";
      
      private var _audioController:IAudioController;
      
      private var _translator:ITranslator;
      
      private var _event:Event;
      
      private var _accountInformations:AccountInformations;
      
      private var _clubModel:ClubModel;
      
      public function TutorialFinishedCommand(param1:IAudioController, param2:ITranslator, param3:Event, param4:AccountInformations, param5:ClubModel)
      {
         super();
         this._audioController = param1;
         this._translator = param2;
         this._event = param3;
         this._accountInformations = param4;
         this._clubModel = param5;
      }
      
      override public function execute() : void
      {
         var channel:String;
         for each(channel in AudioConfiguration.AUDIO_CHANNELS)
         {
            this._audioController.fadeOutAllSounds(channel,500);
         }
         StartUpApplicationCommand.showHome();
      }
   }
}

