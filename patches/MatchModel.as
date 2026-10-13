package com.ankamagames.boufbowl.client.match.model
{
   import as3.collections.ILinkedList;
   import as3.collections.IList;
   import as3.collections.IMap;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.club.model.ClubInformation;
   import com.ankamagames.boufbowl.client.match.event.MatchModelEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.BoufbowlerOrderUpdatedEvent;
   import com.ankamagames.boufbowl.client.match.strategic.event.CombatLogContentEvent;
   import com.ankamagames.boufbowl.client.match.strategic.model.FieldModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufballModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.TeamPanelModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.combatlog.CombatLogModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.grid.GridModel;
   import com.ankamagames.boufbowl.client.match.view.IBoufbowlerSpriteFactory;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.boufbowl.logging.BoufbowlLoggers;
   import com.ankamagames.boufbowl.protocol.BoufbowlerTrack;
   import com.ankamagames.boufbowl.protocol.RankingData;
   import com.ankamagames.boufbowl.protocol.RegularOrderData;
   import com.ankamagames.boufbowl.protocol.ResolutionScenarioMessage;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.boufbowl.resolution.display.animation.IBoufbowlerSprite;
   import com.ankamagames.boufbowl.resolution.display.model.BoufbowlTeam;
   import com.ankamagames.boufbowl.resolution.display.model.IBoufbowler;
   import com.ankamagames.boufbowl.resolution.display.model.SceneModel;
   import com.ankamagames.xgaming.utils.inspection.IEnumConverter;
   import com.ankamagames.xgaming.utils.inspection.enumConverterFor;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.ankamagames.xgaming.utils.math.geom.Point3;
   import com.ankamagames.xgaming.utils.math.geom.hexaToOrtho;
   import com.netease.protobuf.Int64;
   import com.reider.log4AS3.ILogger;
   import org.robotlegs.mvcs.Actor;
   
   public class MatchModel extends Actor
   {
      
      public static const INITIALIZED:String = "com.ankamagames.boufbowl.client.match.model.MatchModel.INITIALIZED";
      
      public static const PLAY_SCRIPT:String = "com.ankamagames.boufbowl.client.match.model.MatchModel.PLAY_SCRIPT";
      
      public static const STATE_CHANGED:String = "com.ankamagames.boufbowl.client.match.event.MatchModel.STATE_CHANGED";
      
      public static const NEW_PHASE:String = "com.ankamagames.boufbowl.client.match.event.MatchModel.NEW_PHASE";
      
      private static const MATCH_STATE_LOGGER:ILogger = LoggerFactory.getStringLogger(BoufbowlLoggers.MATCH_STATE);
      
      private static const MATCH_STATE_ENUM_CONVERTER:IEnumConverter = enumConverterFor(MatchState);
      
      private var _isGivenUp:Boolean;
      
      private var _stateSequentialityValidator:IMatchStateSequentialityValidator;
      
      private var _field:FieldModel;
      
      private var _combatLog:CombatLogModel;
      
      private var _teamPanel:TeamPanelModel;
      
      private var _scene:SceneModel;
      
      private var _grid:GridModel;
      
      private var _chrono:ChronoModel;
      
      private var _boufbowlerSpriteFactory:IBoufbowlerSpriteFactory;
      
      private var _config:IBoufbowlConfig;
      
      private var _stadiumId:int;
      
      private var _tournamentId:Int64;
      
      private var _state:int;
      
      private var _turn:uint;
      
      private var _period:uint;
      
      private var _leftScore:uint;
      
      private var _rightScore:uint;
      
      private var _leftClubInformation:ClubInformation;
      
      private var _rightClubInformation:ClubInformation;
      
      private var _skipIntro:Boolean;
      
      private var _spectator:Boolean;
      
      private var _arrowsDndEnabled:Boolean;
      
      private var _resolutionMessage:ResolutionScenarioMessage;
      
      private var _winnerSide:Number;
      
      public function MatchModel(param1:IMatchStateSequentialityValidator, param2:FieldModel, param3:CombatLogModel, param4:TeamPanelModel, param5:SceneModel, param6:GridModel, param7:ChronoModel, param8:IBoufbowlerSpriteFactory, param9:IBoufbowlConfig)
      {
         super();
         this._stateSequentialityValidator = param1;
         this._stadiumId = this.stadiumId;
         this._field = param2;
         this._combatLog = param3;
         this._teamPanel = param4;
         this._scene = param5;
         this._grid = param6;
         this._chrono = param7;
         this._boufbowlerSpriteFactory = param8;
         this._config = param9;
         this._state = MatchState.NONE;
         this._turn = 0;
         this._leftScore = this._rightScore = 0;
         this._arrowsDndEnabled = true;
         this._winnerSide = NaN;
      }
      
      public function get state() : int
      {
         return this._state;
      }
      
      public function get period() : int
      {
         return this._period;
      }
      
      public function get resolutionMessage() : ResolutionScenarioMessage
      {
         return this._resolutionMessage;
      }
      
      public function get turn() : uint
      {
         return this._turn;
      }
      
      public function get field() : FieldModel
      {
         return this._field;
      }
      
      public function get teamPanel() : TeamPanelModel
      {
         return this._teamPanel;
      }
      
      public function get scene() : SceneModel
      {
         return this._scene;
      }
      
      public function get grid() : GridModel
      {
         return this._grid;
      }
      
      public function get leftScore() : uint
      {
         return this._leftScore;
      }
      
      public function get rightScore() : uint
      {
         return this._rightScore;
      }
      
      public function get leftClubInformation() : ClubInformation
      {
         return this._leftClubInformation;
      }
      
      public function get rightClubInformation() : ClubInformation
      {
         return this._rightClubInformation;
      }
      
      public function get directionArrowsDndEnabled() : Boolean
      {
         return this._arrowsDndEnabled;
      }
      
      public function get skipIntro() : Boolean
      {
         return this._skipIntro;
      }
      
      public function set directionArrowsDndEnabled(param1:Boolean) : void
      {
         this._arrowsDndEnabled = param1;
      }
      
      public function get winnerSide() : Number
      {
         return this._winnerSide;
      }
      
      public function get stadiumId() : int
      {
         return this._stadiumId;
      }
      
      public function get isGivenUp() : Boolean
      {
         return this._isGivenUp;
      }
      
      public function get tournamentId() : Int64
      {
         return this._tournamentId;
      }
      
      public function set tournamentId(param1:Int64) : void
      {
         this._tournamentId = param1;
      }
      
      public function init(param1:ClubInformation, param2:ClubInformation, param3:int, param4:IBoufballModel, param5:ILinkedList, param6:IMap, param7:int, param8:Boolean = false, param9:Boolean = false) : void
      {
         this._period = 0;
         this._leftClubInformation = param1;
         this._rightClubInformation = param2;
         this._field.setup(param3,param4,param5,param6);
         this._teamPanel.setup(param3,param5,param1,param2);
         this._stadiumId = param7;
         this._skipIntro = param8;
         this._spectator = param9;
         if(this._skipIntro)
         {
            this.setState(MatchState.RESUMING);
         }
         dispatch(new MatchModelEvent(INITIALIZED,this));
      }
      
      public function setTurnInformations(param1:uint, param2:uint, param3:uint, param4:uint) : void
      {
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode()
            && this._period != 0 && this._period % 2 != param4 % 2)
         {
            var zones:IIterator = this._field.placementZones.getIterator();
            while(zones.hasNext())
            {
               var cells:Array = zones.getNext();
               for(var index:int = 0; index < cells.length; index++)
               {
                  var cell:HexPoint = cells[index];
                  cells[index] = new HexPoint(-cell.x-cell.y,cell.y);
               }
            }
         }
         this._turn = param1;
         this._leftScore = param2;
         this._rightScore = param3;
         this._period = param4;
      }
      
      public function introduction() : void
      {
         if(!this._stateSequentialityValidator.validate(this.state,MatchState.INTRODUCTION))
         {
            return;
         }
         this.setState(MatchState.INTRODUCTION);
      }
      
      public function startPlacementPhase(param1:int) : void
      {
         var _loc5_:IBoufbowlerInMatchModel = null;
         if(!this._stateSequentialityValidator.validate(this.state,MatchState.PLACEMENT_PHASE))
         {
            return;
         }
         this.setState(MatchState.PLACEMENT_PHASE);
         this._field.displayPlacementZones = true;
         this._field.resetBoufbowlersOrder();
         var _loc2_:Array = [new HexPoint(-21,9),new HexPoint(-20,7),new HexPoint(-19,5),new HexPoint(-18,3),new HexPoint(-17,1),new HexPoint(-16,-1),new HexPoint(-15,-3),new HexPoint(-14,-5),new HexPoint(-13,-7),new HexPoint(-12,-9)];
         var _loc3_:Array = [new HexPoint(12,9),new HexPoint(13,7),new HexPoint(14,5),new HexPoint(15,3),new HexPoint(16,1),new HexPoint(17,-1),new HexPoint(18,-3),new HexPoint(19,-5),new HexPoint(20,-7),new HexPoint(21,-9)];
         var _loc4_:IIterator = this._field.allBoufbowlers.getIterator();
         while(_loc4_.hasNext())
         {
            _loc5_ = _loc4_.getNext();
            _loc5_.position = _loc5_.side == Side.LEFT ? _loc2_.shift() : _loc3_.shift();
         }
         this._field.update();
         this._teamPanel.update();
         dispatch(new MatchModelEvent(NEW_PHASE,this));
         if(this._config.chronoEnabled)
         {
            this._chrono.start(Math.max(param1,0));
         }
      }
      
      public function waitForOpponentPlacement() : void
      {
         if(!this._stateSequentialityValidator.validate(this.state,MatchState.PLACEMENT_PHASE_DONE))
         {
            return;
         }
         this.field.blinkingCell = null;
         this.setState(MatchState.PLACEMENT_PHASE_DONE);
      }
      
      public function startOrderPhase(param1:int, param2:Boolean = true) : void
      {
         if(param2 && !this._stateSequentialityValidator.validate(this.state,MatchState.ORDER_PHASE))
         {
            return;
         }
         this.setState(MatchState.ORDER_PHASE);
         this._field.displayPlacementZones = false;
         this._field.resetBoufbowlersOrder();
         this._field.update();
         this._teamPanel.update();
         dispatch(new MatchModelEvent(NEW_PHASE,this));
         if(this._config.chronoEnabled)
         {
            this._chrono.start(Math.max(param1,0));
         }
      }
      
      public function waitForOpponentOrders() : void
      {
         if(!this._stateSequentialityValidator.validate(this.state,MatchState.ORDER_PHASE_DONE))
         {
            return;
         }
         this.setState(MatchState.ORDER_PHASE_DONE);
      }
      
      public function switchToResolution(param1:ResolutionScenarioMessage) : void
      {
         if(!this._stateSequentialityValidator.validate(this.state,MatchState.RESOLUTION))
         {
            return;
         }
         if(this._chrono.running)
         {
            this._chrono.reset();
         }
         this._resolutionMessage = param1;
         this.applyResolutionBoufbowlerOrders();
         this.setState(MatchState.RESOLUTION);
         this._combatLog.addDataForTurn(this.resolutionMessage.turn,this.resolutionMessage,this._field.boufbowlersOnField);
      }
      
      public function endResolutionPhase() : void
      {
         if(!this._stateSequentialityValidator.validate(this.state,MatchState.RESOLUTION_DONE))
         {
            return;
         }
         this.setState(MatchState.RESOLUTION_DONE);
      }
      
      public function synchronizeSceneModel() : void
      {
         var _loc5_:IBoufbowlerInMatchModel = null;
         var _loc6_:Int64 = null;
         var _loc1_:IList = this.scene.boufbowlers();
         var _loc2_:Int64 = null;
         var _loc3_:IIterator = this.field.allBoufbowlers.getIterator();
         while(_loc3_.hasNext())
         {
            _loc5_ = _loc3_.getNext();
            if(_loc5_.onField)
            {
               _loc1_.removeItem(_loc5_.id);
               this.setupBoufbowlerOnScene(_loc5_);
               if(_loc5_.hasBall)
               {
                  _loc2_ = _loc5_.id;
               }
            }
         }
         var _loc4_:IIterator = _loc1_.getIterator();
         while(_loc4_.hasNext())
         {
            _loc6_ = _loc4_.getNext();
            this.scene.removeBoufbowler(_loc6_);
         }
         if(_loc2_ != null)
         {
            this.scene.ball.holder = this.scene.getBoufbowler(_loc2_);
         }
         else
         {
            this.scene.ball.position = Point3.fromPoint2(hexaToOrtho(this.field.boufball.position));
            this.scene.ball.holder = null;
         }
      }
      
      public function matchEnd(param1:Number, param2:Boolean, param3:int, param4:int, param5:RankingData, param6:RankingData) : void
      {
         this._isGivenUp = param2;
         this._winnerSide = param1;
         this._leftScore = param3;
         this._rightScore = param4;
         this._leftClubInformation.rankingInformation.updateFromRankingData(param5);
         this._rightClubInformation.rankingInformation.updateFromRankingData(param6);
         if(this._chrono.running)
         {
            this._chrono.reset();
         }
         this.setState(MatchState.MATCH_END);
      }
      
      public function hasBoufbowlerAlive() : Boolean
      {
         var _loc3_:IBoufbowlerInMatchModel = null;
         var _loc1_:Boolean = false;
         var _loc2_:IIterator = this.field.boufbowlersOnField.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(_loc3_.side == this.field.side && _loc3_.attributes.health > 0)
            {
               _loc1_ = true;
               break;
            }
         }
         return _loc1_;
      }
      
      public function updateCombatLog() : void
      {
         if(this._combatLog.currentTurn == -1)
         {
            return;
         }
         dispatch(new CombatLogContentEvent(this._combatLog.classOrders,this._combatLog.sortedInteractions,this._combatLog.boufbowlers,this._combatLog.currentTurn,this._combatLog.lastTurn));
      }
      
      internal function setState(param1:uint) : void
      {
         if(this._state == param1)
         {
            return;
         }
         MATCH_STATE_LOGGER.info("{} -> {}",MATCH_STATE_ENUM_CONVERTER.toString(this._state),MATCH_STATE_ENUM_CONVERTER.toString(param1));
         this._state = param1;
         dispatch(new MatchModelEvent(STATE_CHANGED,this));
      }
      
      private function applyResolutionBoufbowlerOrders() : void
      {
         var _loc1_:BoufbowlerTrack = null;
         var _loc2_:IBoufbowlerInMatchModel = null;
         var _loc3_:RegularOrderData = null;
         var _loc4_:int = 0;
         for each(_loc1_ in this._resolutionMessage.boufbowlerTracks)
         {
            _loc2_ = this._field.getBoufbowler(_loc1_.boufbowlerId);
            _loc2_.resetOrder();
            if(_loc1_.order.classOrder)
            {
               _loc2_.order.classOrderActivated = true;
            }
            else
            {
               _loc3_ = _loc1_.order.regularOrder;
               if(_loc3_.hasTargetBoufbowler)
               {
                  _loc2_.order.targetBoufbowler = this._field.getBoufbowler(_loc3_.targetBoufbowler);
               }
               else if(_loc3_.hasTargetCell && _loc3_.elements.length != 0)
               {
                  _loc2_.order.targetCell = new HexPoint(_loc3_.targetCell.x,_loc3_.targetCell.y);
               }
               if(_loc3_.hasPassTargetId)
               {
                  _loc2_.order.passTarget = this._field.getBoufbowler(_loc3_.passTargetId);
               }
               _loc4_ = 0;
               while(_loc4_ < _loc3_.elements.length)
               {
                  _loc2_.order.setElement(_loc4_,_loc3_.elements[_loc4_]);
                  _loc4_++;
               }
            }
            dispatch(new BoufbowlerOrderUpdatedEvent(_loc2_));
         }
      }
      
      private function setupBoufbowlerOnScene(param1:IBoufbowlerInMatchModel) : void
      {
         var _loc2_:IBoufbowler = null;
         var _loc4_:IBoufbowlerSprite = null;
         var _loc3_:BoufbowlTeam = param1.side == Side.LEFT ? BoufbowlTeam.RED : BoufbowlTeam.BLUE;
         if(this.scene.boufbowlers().hasItem(param1.id))
         {
            _loc2_ = this.scene.getBoufbowler(param1.id);
         }
         else
         {
            _loc4_ = this._boufbowlerSpriteFactory.getBoufbowler(param1);
            _loc2_ = this.scene.addBoufbowler(param1.id,_loc4_,_loc3_);
         }
         _loc2_.position = Point3.fromPoint2(hexaToOrtho(param1.position));
         if(_loc3_ == BoufbowlTeam.BLUE)
         {
            _loc2_.direction = 180;
         }
         _loc2_.hasBall = param1.hasBall;
      }
   }
}

