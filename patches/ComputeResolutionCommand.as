package com.ankamagames.boufbowl.client.match.resolution.controller
{
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.ScriptTreeBuilder;
   import com.ankamagames.boufbowl.client.match.model.MatchModel;
   import com.ankamagames.boufbowl.client.match.resolution.builder.IScriptBuilder;
   import com.ankamagames.boufbowl.client.match.resolution.view.ResolutionMediator;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.boufbowl.protocol.ClassOrderInformation;
   import flash.events.Event;
   import flash.system.Capabilities;
   import com.ankamagames.xgaming.utils.flashvars.FlashVarsManager;
   import org.robotlegs.mvcs.Command;
   
   public class ComputeResolutionCommand extends Command
   {
      
      private var _scriptBuilder:IScriptBuilder;
      
      private var _match:MatchModel;
      
      private var _config:IBoufbowlConfig;
      
      public function ComputeResolutionCommand(param1:IScriptBuilder, param2:MatchModel, param3:IBoufbowlConfig)
      {
         super();
         this._scriptBuilder = param1;
         this._match = param2;
         this._config = param3;
      }
      
      override public function execute() : void
      {
         // The browser launcher explicitly requests animation. Do not let an
         // old menu-mode config or a hidden options checkbox silently skip it.
         if(Capabilities.playerType == "PlugIn" &&
            FlashVarsManager(injector.getInstance(FlashVarsManager)).getValue("scene3d") == "1")
            this._config.activate3DScene = true;
         StartUpApplicationCommand.filterBallCutscenes(this._match.resolutionMessage);
         var _loc1_:ClassOrderInformation = null;
         var _loc2_:IBoufbowlerInMatchModel = null;
         for each(_loc1_ in this._match.resolutionMessage.classOrder)
         {
            if(_loc1_.hasZobalMask)
            {
               _loc2_ = this._match.field.getBoufbowler(_loc1_.boufbowlerId);
               _loc2_.currentZobalMask = _loc1_.zobalMask;
            }
         }
         StartUpApplicationCommand.mockPlaybackNotice("Playback mode " + (this._config.activate3DScene ? "3D" : "2D"));
         if(!this._config.activate3DScene)
         {
            dispatch(new Event(ResolutionMediator.SCRIPT_ENDED));
            return;
         }
         this._match.synchronizeSceneModel();
         var tree:ScriptTreeBuilder = this._scriptBuilder.build();
         StartUpApplicationCommand.mockPlaybackNotice("Playback script built");
         dispatch(new PlayScriptEvent(MatchModel.PLAY_SCRIPT,tree));
      }
   }
}

