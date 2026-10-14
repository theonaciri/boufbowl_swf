package com.ankamagames.boufbowl.client.match.controller
{
   import as3.collections.ILinkedList;
   import as3.collections.IMap;
   import as3.collections.LinkedList;
   import as3.collections.Map;
   import com.ankamagames.boufbowl.client.application.IBoufbowlViewDisplayer;
   import com.ankamagames.boufbowl.client.chat.model.IChatModel;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageFactory;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.IMatchColorScheme;
   import com.ankamagames.boufbowl.client.match.model.MatchModel;
   import com.ankamagames.boufbowl.client.match.strategic.FieldFactory;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufballModel;
   import com.ankamagames.boufbowl.client.matchmaking.model.MatchCreationModel;
   import com.ankamagames.boufbowl.client.proto.Converters;
   import com.ankamagames.boufbowl.protocol.BoufballStatus;
   import com.ankamagames.boufbowl.protocol.BoufbowlerData;
   import com.ankamagames.boufbowl.protocol.MatchInformationMessage;
   import com.ankamagames.boufbowl.protocol.Roster;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.boufbowl.protocol.ZoneData;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.math.geom.HexPoint;
   import com.ankamagames.xgaming.utils.protocol.NetworkMessageEvent;
   import org.robotlegs.mvcs.Command;
   
   public class InitializeFieldCommand extends Command
   {
      
      private var _matchCreation:MatchCreationModel;
      
      private var _viewDisplayer:IBoufbowlViewDisplayer;
      
      private var _match:MatchModel;
      
      private var _fieldFactory:FieldFactory;
      
      private var _colorScheme:IMatchColorScheme;
      
      private var _event:NetworkMessageEvent;
      
      private var _translator:ITranslator;
      
      private var _chatModel:IChatModel;
      
      private var _messageFactory:ChatMessageFactory;
      
      public function InitializeFieldCommand(param1:MatchCreationModel, param2:IBoufbowlViewDisplayer, param3:MatchModel, param4:FieldFactory, param5:IMatchColorScheme, param6:NetworkMessageEvent, param7:IChatModel, param8:ITranslator, param9:ChatMessageFactory)
      {
         super();
         this._matchCreation = param1;
         this._viewDisplayer = param2;
         this._match = param3;
         this._fieldFactory = param4;
         this._colorScheme = param5;
         this._event = param6;
         this._chatModel = param7;
         this._translator = param8;
         this._messageFactory = param9;
      }
      
      override public function execute() : void
      {
         com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.setMatchToolbar(true);
         this._matchCreation.clear();
         var _loc1_:MatchInformationMessage = MatchInformationMessage(this._event.message);
         this._fieldFactory.ownSide = _loc1_.side;
         var _loc2_:IBoufballModel = this._fieldFactory.createBoufball(BoufballStatus.ON_GROUND,new HexPoint(0,0));
         this.applySidesColorToScheme(_loc1_);
         this._match.init(Converters.rosterToClubInformation(_loc1_.leftRoster),Converters.rosterToClubInformation(_loc1_.rightRoster),_loc1_.hasSide ? _loc1_.side : -1,_loc2_,this.buildBoufbowlers(_loc1_),this.buildPlacementZones(_loc1_.placementZone),_loc1_.matchStadium,_loc1_.skipIntro,!_loc1_.hasSide);
         this.notifyChat(_loc1_);
      }
      
      private function notifyChat(param1:MatchInformationMessage) : void
      {
         var _loc2_:String = null;
         var _loc3_:String = null;
         var _loc4_:String = null;
         var _loc5_:String = null;
         if(!param1.hasSide || param1.side == Side.LEFT)
         {
            _loc2_ = param1.rightRoster.name;
            _loc3_ = param1.rightRoster.nickname;
            _loc4_ = param1.leftRoster.name;
            _loc5_ = param1.leftRoster.nickname;
         }
         else
         {
            _loc2_ = param1.leftRoster.name;
            _loc3_ = param1.leftRoster.nickname;
            _loc4_ = param1.rightRoster.name;
            _loc5_ = param1.rightRoster.nickname;
         }
         if(param1.hasSide)
         {
            if(this._chatModel != null)
            {
               this._chatModel.addMessage(this._messageFactory.createInfoMessage(this._translator.getText(LangConstants.CHAT_MATCH_STARTED,_loc3_,_loc2_)));
            }
         }
         else if(this._chatModel != null)
         {
            this._chatModel.addMessage(this._messageFactory.createInfoMessage(this._translator.getText(LangConstants.CHAT_MATCH_STARTED_SPECTATOR_MODE,_loc3_,_loc2_,_loc5_,_loc4_)));
         }
      }
      
      private function applySidesColorToScheme(param1:MatchInformationMessage) : void
      {
         var left:Color3=Converters.toColor3(param1.leftRoster.firstColor);
         var right:Color3=Converters.toColor3(param1.rightRoster.firstColor);
         var difference:Number=Math.abs(left.r-right.r)+Math.abs(left.g-right.g)+Math.abs(left.b-right.b);
         var rightColor:uint=difference<90 ? Converters.toColor3(param1.rightRoster.secondColor).toRgbInt() : right.toRgbInt();
         this._colorScheme.setSideColor(Side.LEFT,left.toRgbInt());
         this._colorScheme.setSideColor(Side.RIGHT,rightColor);
      }
      
      private function buildBoufbowlers(param1:MatchInformationMessage) : ILinkedList
      {
         var _loc2_:ILinkedList = new LinkedList();
         var _loc3_:BoufbowlerData = null;
         for each(_loc3_ in param1.leftRoster.characters)
         {
            var leftPlayer:com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel = this._fieldFactory.createBoufbowlerFromData(_loc3_,Side.LEFT);
            if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverZobalMasks[String(_loc3_.id)] != null) leftPlayer.currentZobalMask = int(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverZobalMasks[String(_loc3_.id)]);
            _loc2_.addItem(leftPlayer);
         }
         for each(_loc3_ in param1.rightRoster.characters)
         {
            var rightPlayer:com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel = this._fieldFactory.createBoufbowlerFromData(_loc3_,Side.RIGHT);
            if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverZobalMasks[String(_loc3_.id)] != null) rightPlayer.currentZobalMask = int(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverZobalMasks[String(_loc3_.id)]);
            _loc2_.addItem(rightPlayer);
         }
         return _loc2_;
      }
      
      private function buildPlacementZones(param1:Array) : IMap
      {
         var _loc3_:ZoneData = null;
         var _loc2_:IMap = new Map();
         for each(_loc3_ in param1)
         {
            _loc2_.addItem(_loc3_.type,_loc3_.cell.map(Converters.toHexPoint));
         }
         return _loc2_;
      }
   }
}

