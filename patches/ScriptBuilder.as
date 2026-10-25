package com.ankamagames.boufbowl.client.match.resolution.builder
{
   import as3.collections.IList;
   import as3.collections.IMap;
   import as3.collections.LinkedList;
   import as3.collections.Map;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.client.match.IMatchColorScheme;
   import com.ankamagames.boufbowl.client.match.model.MatchModel;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.BoufbowlerMovementFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.BoufbowlerSetupFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.CameraSetupFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.CameraZoomFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.ClassOrderBuffFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.ClassOrderDebuffFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.DeathFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.PeriodFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.PlayAmbianceFunction;
   import com.ankamagames.boufbowl.client.match.resolution.interactions.StepsSoundFunction;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.RulesConstants;
   import com.ankamagames.boufbowl.client.proto.Converters;
   import com.ankamagames.boufbowl.config.IStadiumsConfig;
   import com.ankamagames.boufbowl.logging.BoufbowlLoggers;
   import com.ankamagames.boufbowl.protocol.BoufbowlerClass;
   import com.ankamagames.boufbowl.protocol.BoufbowlerTrack;
   import com.ankamagames.boufbowl.protocol.ClassOrderInformation;
   import com.ankamagames.boufbowl.protocol.InteractionEntry;
   import com.ankamagames.boufbowl.protocol.MovementSequence;
   import com.ankamagames.boufbowl.protocol.ResolutionScenarioMessage;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.boufbowl.protocol.Stadium;
   import com.ankamagames.boufbowl.protocol.TrackItem;
   import com.ankamagames.boufbowl.protocol.TrackItemType;
   import com.ankamagames.boufbowl.resolution.display.script.ParticipantData;
   import com.ankamagames.boufbowl.resolution.display.script.ScriptConstants;
   import com.ankamagames.boufbowl.resolution.display.script.runner.action.EndAction;
   import com.ankamagames.boufbowl.resolution.display.script.runner.action.StopAllSoundsAction;
   import com.ankamagames.boufbowl.resolution.display.script.runner.action.WaitAction;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.ActionNode;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.INode;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.JoinNode;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.ParallelNode;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.ScriptTreeBuilder;
   import com.ankamagames.boufbowl.resolution.display.script.runner.structure.SequentialNode;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.errors.IllegalArgumentError;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.reider.log4AS3.ILogger;

   public class ScriptBuilder implements IScriptBuilder
   {

      private static const LOGGER_ERROR:ILogger = LoggerFactory.getStringLogger(BoufbowlLoggers.RUNTIME_ERROR);

      private static const MS_PER_TICK:Number = 50;

      private var _match:MatchModel;

      private var _message:ResolutionScenarioMessage;

      private var _stadiumsConfig:IStadiumsConfig;

      private var _matchColorScheme:IMatchColorScheme;

      private var _constants:RulesConstants;

      private var _translator:ITranslator;

      private var _commonData:CommonData;

      private var _woundedBoufbowlersThisTurn:IList = new LinkedList();

      private var _computedInteractions:IMap;
      private var _previousInteractions:IMap = new Map();

      private var _ballOnlyInteractions:IList;

      private var _interactionsJoinForkNodes:IMap = new Map();

      public function ScriptBuilder(param1:MatchModel, param2:IStadiumsConfig, param3:IMatchColorScheme, param4:RulesConstants, param5:ITranslator)
      {
         super();
         this._match = param1;
         this._message = param1.resolutionMessage;
         this._stadiumsConfig = param2;
         this._constants = param4;
         this._matchColorScheme = param3;
         this._translator = param5;
         this._ballOnlyInteractions = new LinkedList();
      }

      public function build() : ScriptTreeBuilder
      {
         var mainNode:SequentialNode;
         var script:ScriptTreeBuilder;
         this._commonData = new CommonData(this._match,MS_PER_TICK);
         this.buildBoufbowlersInfos();
         this.buildBallTrajectory();
         this.computeInteractions();
         mainNode = new SequentialNode();
         mainNode.addNode(this.computeSetup());
         try
         {
            mainNode.addNode(this.computeResolution());
         }
         catch(error:*)
         {
            LOGGER_ERROR.error("Exception pendant le calcul de la résolution : {}",error);
         }
         mainNode.addNode(this.computeEndSequence());
         script = new ScriptTreeBuilder();
         script.addNode(0,mainNode);
         script.removeDuplicatedNodes();
         script.simplify();
         return script;
      }

      private function buildBoufbowlersInfos() : void
      {
         var track:BoufbowlerTrack = null;
         var infos:BoufbowlerInfos = null;
         var item:TrackItem = null;
         for each(track in this._message.boufbowlerTracks)
         {
            infos = new BoufbowlerInfos(track.boufbowlerId,track.order);
            for each(item in BoufbowlerMovementFunction.presentationItems(track.item))
            {
               if(item.type != TrackItemType.MOVEMENT)
               {
                  infos.addTrajectory(item.movement.startTick,item.movement.endTick,item.movement.positions.map(Converters.toHexPoint),item.interactionId);
               }
               else
               {
                  infos.addTrajectory(item.movement.startTick,item.movement.endTick,item.movement.positions.map(Converters.toHexPoint));
               }
            }
            this._commonData.addBoufbowlerInfos(infos);
         }
      }

      private function buildBallTrajectory() : void
      {
         var _loc1_:BoufballTrackBuilder = new BoufballTrackBuilder();
         this._commonData.boufballTrack = _loc1_.build(this._message,this._match.field.boufball.position,this._commonData);
      }

      private function computeInteractions() : void
      {
         var _loc2_:InteractionEntry = null;
         var _loc3_:INode = null;
         var _loc1_:InteractionComputer = new InteractionComputer(this._match,this._stadiumsConfig,this._message,this._commonData);
         this._computedInteractions = new Map();
         var ordered:Array = this._message.interaction.concat();
         ordered.sort(function(a:InteractionEntry,b:InteractionEntry):Number {
            return a.interactionDetails.startTick - b.interactionDetails.startTick || a.interactionId - b.interactionId;
         });
         var previous:INode = null;
         for each(_loc2_ in ordered)
         {
            _loc3_ = _loc1_.compute(_loc2_);
            // Dependencies serialize outcomes even when their animation lengths
            // differ from the estimated wire duration. Movement stays parallel.
            _loc3_.structuralNode = true;
            this._previousInteractions.addItem(_loc2_.interactionId,previous);
            previous = _loc3_;
            if(_loc2_.interactionDetails.participants.length == 0)
            {
               this._ballOnlyInteractions.addItem(_loc2_);
            }
            this._computedInteractions.addItem(_loc2_.interactionId,_loc3_);
            LOGGER_ERROR.info("computedInteraction : {}",_loc3_);
         }
         this._woundedBoufbowlersThisTurn = _loc1_.woundedBoufbowlers;
      }

      private function computeSetup() : INode
      {
         var _loc1_:SequentialNode = new SequentialNode();
         _loc1_.addNode(this.computePlayAmbiance());
         _loc1_.addNode(this.computeCameraSetup());
         _loc1_.addNode(this.computeBoufbowlersSetup());
         _loc1_.addNode(this.computeBoufbowlersClassOrder());
         _loc1_.addNode(this.computeCameraZoom());
         return _loc1_;
      }

      private function computePlayAmbiance() : INode
      {
         var _loc1_:String = this._stadiumsConfig.getStadiumData(this._match.stadiumId).ambiantTrackName;
         if(_loc1_ == null || _loc1_.length == 0)
         {
            return new SequentialNode();
         }
         return new PlayAmbianceFunction(_loc1_).getNode();
      }

      private function computeCameraSetup() : INode
      {
         return new CameraSetupFunction(this._match.stadiumId).getNode();
      }

      private function computeBoufbowlersSetup() : INode
      {
         var _loc2_:BoufbowlerTrack = null;
         var _loc3_:ParticipantData = null;
         var _loc4_:BoufbowlerSetupFunction = null;
         var _loc1_:ParallelNode = new ParallelNode();
         _loc1_.structuralNode = true;
         _loc1_.label = "setup";
         for each(_loc2_ in this._message.boufbowlerTracks)
         {
            _loc3_ = this._match.field.getBoufbowler(_loc2_.boufbowlerId).toParticipantData();
            _loc4_ = new BoufbowlerSetupFunction(_loc3_);
            _loc1_.addNode(_loc4_.getNode());
         }
         return _loc1_;
      }

      private function computeBoufbowlersClassOrder() : INode
      {
         var _loc1_:SequentialNode = new SequentialNode();
         this.addBoufbowlersClassOrder(_loc1_,true);
         this.addBoufbowlersClassOrder(_loc1_,false);
         return _loc1_;
      }

      private function addBoufbowlersClassOrder(param1:SequentialNode, param2:Boolean) : void
      {
         var _loc3_:ClassOrderInformation = null;
         var _loc4_:IBoufbowlerInMatchModel = null;
         for each(_loc3_ in this._message.classOrder)
         {
            _loc4_ = this._match.field.getBoufbowler(_loc3_.boufbowlerId);
            if(param2 == (_loc4_.boufbowlerClass == BoufbowlerClass.ECAFLIP))
            {
               param1.addNode(new ClassOrderBuffFunction(_loc4_.toParticipantData(),_loc4_.boufbowlerClass,_loc3_.target,_loc3_.hasZobalMask ? _loc3_.zobalMask : NaN).getNode());
            }
         }
      }

      private function computeCameraZoom() : INode
      {
         return new CameraZoomFunction().getNode();
      }

      private function computeStopAmbiance() : INode
      {
         return new ActionNode(new StopAllSoundsAction(AudioConfiguration.AMBIANT,500));
      }

      private function computeResolution() : INode
      {
         var track:BoufbowlerTrack = null;
         var ballInteractions:IIterator = null;
         var infos:BoufbowlerInfos = null;
         var item:TrackItem = null;
         var interaction:InteractionEntry = null;
         var interactionNode:INode = null;
         var ballSequence:SequentialNode = null;
         var waitForBall:ActionNode = null;
         var root:ParallelNode = new ParallelNode();
         root.structuralNode = true;
         root.label = "Root Node";
         var stepsNode:INode = this.computeStepsSound();
         stepsNode.structuralNode = true;
         stepsNode.label = "stepNode";
         stepsNode.simplify();
         root.addNode(stepsNode);
         for each(track in this._message.boufbowlerTracks)
         {
            infos = this._commonData.getBoufbowlerInfos(track.boufbowlerId);
            this.addBoufbowlerStartNode(infos,root);
            for each(item in BoufbowlerMovementFunction.presentationItems(track.item))
            {
               if(item.type == TrackItemType.MOVEMENT)
               {
                  this.addMovementNode(infos,item.movement);
               }
               else if(item.type == TrackItemType.INTERACTION)
               {
                  this.addInteractionNode(infos,item.interactionId,root);
               }
            }
         }
         ballInteractions = this._ballOnlyInteractions.getIterator();
         while(ballInteractions.hasNext())
         {
            interaction = ballInteractions.getNext();
            interactionNode = this.getComputedInteraction(interaction.interactionId);
            ballSequence = new SequentialNode();
            waitForBall = this.waitNode(interaction.interactionDetails.startTick * ScriptConstants.TICK_TO_MS);
            var ballGate:JoinNode = new JoinNode();
            ballGate.structuralNode = true;
            ballGate.addNode(waitForBall);
            this.addPreviousInteraction(ballGate,interaction.interactionId);
            root.addNode(waitForBall);
            ballSequence.addNode(ballGate);
            ballSequence.addNode(interactionNode);
            root.addNode(ballSequence);
         }
         return root;
      }

      private function computeStepsSound() : INode
      {
         var _loc1_:IList = new MovingBoufbowlersByTickBuilder().build(this._message,this._commonData);
         return new StepsSoundFunction(_loc1_,this._commonData.msPerTick).getNode();
      }

      private function addMovementNode(param1:BoufbowlerInfos, param2:MovementSequence) : void
      {
         var _loc3_:ParticipantData = this._commonData.relatedTurnParticipantData(param2.startTick,param1.boufbowlerId);
         var _loc4_:INode = new BoufbowlerMovementFunction(_loc3_,(param2.endTick - param2.startTick) * this._commonData.msPerTick).getNode();
         param1.sequentialNode.addNode(_loc4_);
      }

      private function addInteractionNode(param1:BoufbowlerInfos, param2:uint, param3:ParallelNode) : void
      {
         var _loc5_:SequentialNode = null;
         var _loc6_:JoinNode = null;
         var _loc7_:ParallelNode = null;
         var _loc4_:JoinForkNode = this._interactionsJoinForkNodes.getItem(param2);
         if(_loc4_ == null)
         {
            _loc5_ = new SequentialNode();
            _loc5_.structuralNode = true;
            _loc5_.label = "interactionSequence " + param2;
            _loc6_ = new JoinNode();
            _loc6_.structuralNode = true;
            _loc6_.label = "interactionJoin" + param2;
            this.addPreviousInteraction(_loc6_,param2);
            _loc5_.addNode(_loc6_);
            _loc5_.addNode(this.getComputedInteraction(param2));
            _loc7_ = new ParallelNode();
            _loc7_.structuralNode = true;
            _loc7_.label = "interactionFork" + param2;
            _loc5_.addNode(_loc7_);
            param3.addNode(_loc5_);
            _loc4_ = new JoinForkNode(_loc6_,_loc7_);
            this._interactionsJoinForkNodes.addItem(param2,_loc4_);
         }
         _loc4_.joinNode.addNode(param1.sequentialNode);
         param1.sequentialNode = new SequentialNode();
         param1.sequentialNode.structuralNode = true;
         param1.sequentialNode.label = "boufbowler " + param1.boufbowlerId;
         _loc4_.forkNode.addNode(param1.sequentialNode);
      }

      private function addPreviousInteraction(gate:JoinNode, identity:uint) : void
      {
         var previous:INode = this._previousInteractions.getItem(identity);
         if(previous != null) gate.addNode(previous);
      }

      private function addBoufbowlerStartNode(param1:BoufbowlerInfos, param2:ParallelNode) : void
      {
         param1.sequentialNode.structuralNode = true;
         param1.sequentialNode.label = "startNode " + param1.boufbowlerId;
         param2.addNode(param1.sequentialNode);
      }

      private function computeEndSequence(param1:Boolean = true) : INode
      {
         var _loc2_:SequentialNode = new SequentialNode();
         _loc2_.structuralNode = true;
         _loc2_.label = "end";
         _loc2_.addNode(this.waitNode(ScriptConstants.RESOLUTION_END_DURATION));
         _loc2_.addNode(this.computeBoufbowlersDebuff());
         if(param1 && this._woundedBoufbowlersThisTurn.numItems != 0)
         {
            _loc2_.addNode(this.computeWoundedBoufbowlersNode());
         }
         _loc2_.addNode(this.computeStopAmbiance());
         if(this._message.hasPeriodInformations)
         {
            _loc2_.addNode(new PeriodFunction(this._message.periodInformations,Color3.fromRgbUInt(this._matchColorScheme.getSideColor(this._match.field.side != -1 ? this._match.field.side : Side.LEFT)),this._translator,this._constants.getMaxPeriodNumber(this._match.stadiumId),this._match.stadiumId == Stadium.BONTA ? ScriptConstants.ZOOM_START_TURN : ScriptConstants.ZOOM_MIN).getNode());
         }
         _loc2_.addNode(this.endNode());
         return _loc2_;
      }

      private function computeBoufbowlersDebuff() : INode
      {
         var _loc2_:ClassOrderInformation = null;
         var _loc1_:SequentialNode = new SequentialNode();
         for each(_loc2_ in this._message.classOrder)
         {
            _loc1_.addNode(new ClassOrderDebuffFunction(_loc2_.target).getNode());
         }
         return _loc1_;
      }

      private function computeWoundedBoufbowlersNode() : INode
      {
         var _loc4_:ParticipantData = null;
         var _loc1_:SequentialNode = new SequentialNode();
         _loc1_.structuralNode = true;
         _loc1_.label = "wounds";
         var _loc2_:ParallelNode = new ParallelNode();
         var _loc3_:IIterator = this._woundedBoufbowlersThisTurn.getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext();
            _loc2_.addNode(new DeathFunction(_loc4_).getNode());
         }
         _loc1_.addNode(_loc2_);
         _loc1_.addNode(this.waitNode(ScriptConstants.WOUNDED_BOUFBOWLERS_END_DURATION));
         return _loc1_;
      }

      private function getComputedInteraction(param1:uint) : INode
      {
         return this._computedInteractions.getItem(param1);
      }

      private function waitNode(param1:Number) : ActionNode
      {
         if(param1 <= 0)
         {
            throw IllegalArgumentError("Can\'t wait with 0 or negative duration, value is " + param1);
         }
         return new ActionNode(new WaitAction(param1));
      }

      private function endNode() : ActionNode
      {
         return new ActionNode(new EndAction());
      }
   }
}
