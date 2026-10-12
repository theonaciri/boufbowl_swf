package com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.controller
{
   import com.ankamagames.boufbowl.client.application.messagebox.event.MessageBoxEvent;
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.strategic.model.IClubBoufbowlerModel;
   import com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.model.BoufbowlerEditionModel;
   import com.ankamagames.boufbowl.client.proto.ProtocolMessageBuilder;
   import com.ankamagames.boufbowl.protocol.CustomisationType;
   import com.ankamagames.xgaming.net.channel.pipeline.ChannelPipeline;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   [Inject(name="LOBBY")]
   public class SendBoufbowlerCustomisationChangeCommand extends ModuleCommand
   {
      
      private var _pipeline:ChannelPipeline;
      
      private var _boufbowlerEdition:BoufbowlerEditionModel;
      
      private var _messageBuilder:ProtocolMessageBuilder;
      
      private var _translator:ITranslator;
      
      public function SendBoufbowlerCustomisationChangeCommand(param1:ChannelPipeline, param2:BoufbowlerEditionModel, param3:ProtocolMessageBuilder, param4:ITranslator)
      {
         super();
         this._pipeline = param1;
         this._boufbowlerEdition = param2;
         this._messageBuilder = param3;
         this._translator = param4;
      }
      
      override public function execute() : void
      {
         var current:ClubModel = injector.getInstance(ClubModel);
         var edited:ClubModel = this._boufbowlerEdition.customizedClub;
         current.setup(edited.clubInformation,edited.boufbowlers,false);
         StartUpApplicationCommand.showHome();
      }
   }
}

