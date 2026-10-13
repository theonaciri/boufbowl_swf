package com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller
{
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.application.messagebox.event.MessageBoxEvent;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.strategic.model.IClubBoufbowlerModel;
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.model.ClubColorSelectionModel;
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.model.ClubEditionModel;
   import com.ankamagames.boufbowl.client.proto.ProtocolMessageBuilder;
   import com.ankamagames.boufbowl.protocol.ClubAppearanceChangeMessage;
   import com.ankamagames.boufbowl.protocol.CustomisationType;
   import com.ankamagames.boufbowl.protocol.ForcedFullTeamChangeMessage;
   import com.ankamagames.boufbowl.protocol.FullTeamChange;
   import com.ankamagames.boufbowl.protocol.FullTeamChangeMessage;
   import com.ankamagames.xgaming.net.channel.pipeline.ChannelPipeline;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.netease.protobuf.Message;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   [Inject(name="LOBBY")]
   public class SendClubCustomisationChangeCommand extends ModuleCommand
   {
      
      private var _protocolMessageBuilder:ProtocolMessageBuilder;
      
      private var _pipeline:ChannelPipeline;
      
      private var _clubEdition:ClubEditionModel;
      
      private var _clubColorSelection:ClubColorSelectionModel;
      
      private var _translator:ITranslator;
      
      public function SendClubCustomisationChangeCommand(param1:ChannelPipeline, param2:ClubEditionModel, param3:ClubColorSelectionModel, param4:ITranslator, param5:ProtocolMessageBuilder)
      {
         super();
         this._pipeline = param1;
         this._clubEdition = param2;
         this._clubColorSelection = param3;
         this._translator = param4;
         this._protocolMessageBuilder = param5;
      }
      
      override public function execute() : void
      {
         var current:ClubModel = injector.getInstance(ClubModel);
         var edited:ClubModel = this._clubEdition.customizedClub;
         current.setup(edited.clubInformation,edited.boufbowlers,false);
         StartUpApplicationCommand.persistClub(current);
         StartUpApplicationCommand.showHome();
      }
      
      private function sendMessage(param1:Message) : void
      {
         this.displayWaiting();
         this._pipeline.sendDownstream(param1);
      }
      
      private function buildClubRebuildMessage() : ForcedFullTeamChangeMessage
      {
         var _loc1_:ForcedFullTeamChangeMessage = new ForcedFullTeamChangeMessage();
         _loc1_.change = this.buildFullTeamChange();
         return _loc1_;
      }
      
      private function buildClubAppearanceChange() : ClubAppearanceChangeMessage
      {
         return this._protocolMessageBuilder.buildClubAppearanceMessage(this._clubEdition,this._clubColorSelection);
      }
      
      private function buildFullTeamChangeMessage() : FullTeamChangeMessage
      {
         var _loc1_:FullTeamChangeMessage = new FullTeamChangeMessage();
         _loc1_.change = this.buildFullTeamChange();
         return _loc1_;
      }
      
      private function buildFullTeamChange() : FullTeamChange
      {
         var _loc1_:FullTeamChange = new FullTeamChange();
         _loc1_.clubAppearanceChange = this._protocolMessageBuilder.buildClubAppearanceMessage(this._clubEdition,this._clubColorSelection);
         _loc1_.boufbowlerAttributesChange = this.getBoufbowlersAttributesArray();
         return _loc1_;
      }
      
      private function getBoufbowlersAttributesArray() : Array
      {
         var _loc3_:IClubBoufbowlerModel = null;
         var _loc1_:Array = [];
         var _loc2_:IIterator = this._clubEdition.customizedClub.boufbowlers.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            _loc1_.push(this._protocolMessageBuilder.buildBoufbowlerAttributesChangeMessage(_loc3_));
         }
         return _loc1_;
      }
      
      private function displayWaiting() : void
      {
         dispatchToModules(MessageBoxEvent.waiting(this._translator.getText(LangConstants.PREMIUMSERVICE_CUSTOMISATION_WAITING)));
      }
   }
}

