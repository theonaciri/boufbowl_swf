package com.ankamagames.boufbowl.client.match.controller
{
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.client.match.RandomMusicChooser;
   import com.ankamagames.boufbowl.client.match.event.MatchModelEvent;
   import com.ankamagames.boufbowl.client.match.model.MatchState;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.xgaming.audio.controller.IAudioController;
   import com.ankamagames.xgaming.audio.controller.data.AudioRequest;
   import com.ankamagames.xgaming.audio.controller.data.LoopsData;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.reider.log4AS3.ILogger;
   import flash.net.URLRequest;
   import org.robotlegs.mvcs.Command;

   public class ChooseMusicCommand extends Command
   {

      private var _musicChooser:RandomMusicChooser;

      private var _audioController:IAudioController;

      private var _config:IBoufbowlConfig;

      private var _event:MatchModelEvent;

      private var LOGGER:ILogger = LoggerFactory.getLogger(ChooseMusicCommand);

      public function ChooseMusicCommand(param1:RandomMusicChooser, param2:IAudioController, param3:IBoufbowlConfig, param4:MatchModelEvent)
      {
         super();
         this._musicChooser = param1;
         this._audioController = param2;
         this._config = param3;
         this._event = param4;
      }

      override public function execute() : void
      {
         var track:String = null;
         switch(this._event.match.state)
         {
            case MatchState.RESUMING:
            case MatchState.INTRODUCTION:
               break;
            case MatchState.PLACEMENT_PHASE:
               track = "music/music_tactic_loop_01.mp3";
               break;
            case MatchState.PLACEMENT_PHASE_DONE:
               break;
            case MatchState.ORDER_PHASE:
               track = "music/music_tactic_loop_01.mp3";
               break;
            case MatchState.ORDER_PHASE_DONE:
               break;
            case MatchState.RESOLUTION:
               track = "music/music_resolution_loop_01.mp3";
               break;
            case MatchState.RESOLUTION_DONE:
               break;
            case MatchState.MATCH_END:
               this.fadeSounds();
               break;
            default:
               throw new IllegalStateError("Not handled match state : " + this._event.match.state);
         }
         if(track != null)
         {
            this.LOGGER.info("will play : {}",track);
            this._audioController.playSound(AudioConfiguration.MUSIC,new AudioRequest(new URLRequest(this._config.soundBasePath + track),null,null,LoopsData.MAX_LOOPS));
         }
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
