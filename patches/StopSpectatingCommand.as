package com.ankamagames.boufbowl.client.match.controller
{
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.client.application.BoufbowlViews;
   import com.ankamagames.boufbowl.protocol.StopSpectatingMessage;
   import com.ankamagames.xgaming.audio.controller.IAudioController;
   import com.ankamagames.xgaming.net.channel.pipeline.ChannelPipeline;
   import com.ankamagames.xgaming.utils.injection.module.event.DisplayViewEvent;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   [Inject(name="MATCH")]
   public class StopSpectatingCommand extends ModuleCommand
   {
      
      private var _matchPipeline:ChannelPipeline;
      
      private var _audioController:IAudioController;
      
      public function StopSpectatingCommand(param1:ChannelPipeline, param2:IAudioController)
      {
         super();
         this._matchPipeline = param1;
         this._audioController = param2;
      }
      
      override public function execute() : void
      {
         com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.setMatchToolbar(false);
         this._matchPipeline.sendDownstream(new StopSpectatingMessage());
         this.fadeSounds();
         dispatchToModules(new DisplayViewEvent(BoufbowlViews.MATCHMAKING));
      }
      
      private function fadeSounds() : void
      {
         this._audioController.fadeOutAllSounds(AudioConfiguration.AMBIANT,2000);
         this._audioController.fadeOutAllSounds(AudioConfiguration.FOLEY,2000);
         this._audioController.fadeOutAllSounds(AudioConfiguration.FX,2000);
         this._audioController.fadeOutAllSounds(AudioConfiguration.MUSIC,2000);
         this._audioController.fadeOutAllSounds(AudioConfiguration.STEPS,2000);
      }
   }
}

