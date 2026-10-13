package com.ankamagames.boufbowl.client.clubselection.controller
{
   import as3.collections.ArrayList;
   import as3.collections.IArrayList;
   import com.ankamagames.boufbowl.client.application.BoufbowlViews;
   import com.ankamagames.boufbowl.client.club.model.ClubBoufbowlerFactory;
   import com.ankamagames.boufbowl.client.club.model.ClubInformation;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.proto.ProtocolMessageBuilder;
   import com.ankamagames.boufbowl.protocol.ItemAvailability;
   import com.ankamagames.boufbowl.protocol.PredefinedClubInformation;
   import com.ankamagames.boufbowl.protocol.PredefinedClubsMessage;
   import com.ankamagames.boufbowl.protocol.SigilBackground;
   import com.ankamagames.boufbowl.protocol.SigilCharge;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.injection.module.event.DisplayViewEvent;
   import com.ankamagames.xgaming.utils.protocol.NetworkMessageEvent;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class PredefinedClubsCommand extends ModuleCommand
   {
      
      private var _club:ClubModel;
      
      private var _clubBoufbowlerFactory:ClubBoufbowlerFactory;
      
      private var _event:NetworkMessageEvent;
      
      public function PredefinedClubsCommand(param1:ClubModel, param2:ClubBoufbowlerFactory, param3:NetworkMessageEvent)
      {
         super();
         this._club = param1;
         this._clubBoufbowlerFactory = param2;
         this._event = param3;
      }
      
      override public function execute() : void
      {
         var _loc1_:PredefinedClubsMessage = PredefinedClubsMessage(this._event.message);
         this._club.predefinedClubs = this.clubs(_loc1_.club);
         dispatchToModules(new DisplayViewEvent(BoufbowlViews.CLUB_SELECTION));
      }
      
      private function clubs(param1:Array) : IArrayList
      {
         var _loc3_:PredefinedClubInformation = null;
         var _loc2_:IArrayList = new ArrayList();
         for each(_loc3_ in param1)
         {
            _loc2_.addItem(this.predefClub(_loc3_));
         }
         return _loc2_;
      }
      
      private function predefClub(param1:PredefinedClubInformation) : ClubModel
      {
         var _loc2_:ClubModel = new ClubModel();
         _loc2_.setup(new ClubInformation(param1.clubId,"",SigilBackground.IBERIAN_BEND_SINISTER,SigilCharge.BOUCLIER,0,null,null,null),this._clubBoufbowlerFactory.createBoufbowlersFromData(param1.boufbowler,ItemAvailability.BASE,ProtocolMessageBuilder.colorData(Color3.BLACK)),true);
         return _loc2_;
      }
   }
}

