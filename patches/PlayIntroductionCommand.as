package com.ankamagames.boufbowl.client.match.controller
{
   import com.ankamagames.boufbowl.client.club.view.IllustrationViewFactory;
   import com.ankamagames.boufbowl.client.match.model.MatchModel;
   import com.ankamagames.boufbowl.client.match.resolution.controller.PlayScriptEvent;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.VersusFunction;
   import com.ankamagames.boufbowl.client.match.resolution.view.ResolutionMediator;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.boufbowl.config.IStadiumsConfig;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.boufbowl.resolution.display.script.CommonInteractionFunctions;
   import com.ankamagames.boufbowl.resolution.display.script.runner.action.EndAction;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.ActionNode;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.INode;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.ScriptTreeBuilder;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import flash.events.Event;
   import flash.system.ApplicationDomain;
   import org.robotlegs.mvcs.Command;
   
   public class PlayIntroductionCommand extends Command
   {
      
      private var _translator:ITranslator;
      
      private var _illustrationFactory:IllustrationViewFactory;
      
      private var _match:MatchModel;
      
      private var _config:IBoufbowlConfig;
      
      private var _stadiumsConfig:IStadiumsConfig;
      
      public function PlayIntroductionCommand(param1:MatchModel, param2:IBoufbowlConfig, param3:IStadiumsConfig, param4:IllustrationViewFactory, param5:ITranslator)
      {
         super();
         this._match = param1;
         this._config = param2;
         this._stadiumsConfig = param3;
         this._illustrationFactory = param4;
         this._translator = param5;
      }
      
      override public function execute() : void
      {
         if(this._match.skipIntro)
         {
            return;
         }
         com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.mockPlaybackNotice("Match introduction started");
         this._match.introduction();
         if(!this._config.activate3DScene)
         {
            dispatch(new Event(ResolutionMediator.SCRIPT_ENDED));
            return;
         }
         this._match.field.boufball.position = new HexPoint(30,-60);
         this._match.synchronizeSceneModel();
         var _loc1_:ScriptTreeBuilder = new ScriptTreeBuilder();
         var _loc2_:INode = this.getIntroductionNode();
         var _loc3_:INode = this.getVersusNode();
         var _loc4_:INode = new ActionNode(new EndAction());
         _loc1_.addNode(0,_loc2_);
         _loc1_.addNodeAfter(_loc2_,_loc3_);
         _loc1_.addNodeAfter(_loc3_,_loc4_);
         _loc1_.removeDuplicatedNodes();
         _loc1_.simplify();
         dispatch(new PlayScriptEvent(MatchModel.PLAY_SCRIPT,_loc1_));
      }
      
      private function getIntroductionNode() : INode
      {
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode()) return new com.ankamagames.boufbowl.client.match.resolution.interactions.IntroStadiumFarm().getNode();
         var _loc1_:CommonInteractionFunctions = new (ApplicationDomain.currentDomain.getDefinition(this._stadiumsConfig.getStadiumData(this._match.stadiumId).introScriptClass))();
         return _loc1_.getNode();
      }
      
      private function getVersusNode() : INode
      {
         return new VersusFunction(this._match.leftClubInformation,this._match.rightClubInformation,this._match.field.getSideCaptain(Side.LEFT),this._match.field.getSideCaptain(Side.RIGHT),this._illustrationFactory,this._translator).getNode();
      }
   }
}

