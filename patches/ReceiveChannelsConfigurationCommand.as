package com.ankamagames.boufbowl.client.chat.controller.channel
{
   import as3.collections.IList;
   import com.ankamagames.boufbowl.client.chat.model.IChatModel;
   import com.ankamagames.boufbowl.client.chat.model.channel.ChannelInformation;
   import com.ankamagames.boufbowl.client.chat.model.channel.ChannelInformationsFactory;
   import com.ankamagames.boufbowl.client.chat.model.channel.ClientChannelType;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageData;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageFactory;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.login.model.AccountInformations;
   import com.ankamagames.xgaming.chat.protocol.ChannelAvailableNotificationMessage;
   import com.ankamagames.xgaming.chat.protocol.ChannelOptionMessage;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.protocol.NetworkMessageEvent;
   import org.robotlegs.mvcs.Command;
   
   public class ReceiveChannelsConfigurationCommand extends Command
   {
      
      private var _chatModel:IChatModel;
      
      private var _channelInfosFactory:ChannelInformationsFactory;
      
      private var _triggerEvent:NetworkMessageEvent;
      
      private var _chatMessageFactory:ChatMessageFactory;
      
      private var _translator:ITranslator;
      
      private var _accountInformations:AccountInformations;
      
      public function ReceiveChannelsConfigurationCommand(param1:NetworkMessageEvent, param2:IChatModel, param3:ChannelInformationsFactory, param4:ChatMessageFactory, param5:ITranslator, param6:AccountInformations)
      {
         super();
         this._chatModel = param2;
         this._channelInfosFactory = param3;
         this._triggerEvent = param1;
         this._chatMessageFactory = param4;
         this._translator = param5;
         this._accountInformations = param6;
      }
      
      override public function execute() : void
      {
         var _loc2_:ChannelInformation = null;
         var _loc3_:ChannelOptionMessage = null;
         var _loc1_:Array = [];
         for each(_loc3_ in ChannelAvailableNotificationMessage(this._triggerEvent.message).options)
         {
            _loc2_ = this._channelInfosFactory.create(_loc3_);
            this._chatModel.addAvailableChannel(_loc2_);
            var registered:Boolean = !_loc3_.subscriptionManagedByClient || (com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode() && _loc2_.channelType == ClientChannelType.GENERAL && com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverSubscribed(_loc2_.lang));
            if(registered)
            {
               this._chatModel.registerToChannel(_loc2_.channelType,_loc2_.lang);
            }
            if(_loc3_.writable && registered)
            {
               _loc1_.push(_loc2_);
            }
         }
         this.activateDefaultChannel(_loc1_);
      }
      
      private function activateDefaultChannel(param1:Array) : void
      {
         var selected:ChannelInformation = null;
         for each(var channel:ChannelInformation in param1)
         {
            if(channel.channelType == ClientChannelType.MATCH)
            {
               this._chatModel.selectActiveChannel(ClientChannelType.MATCH);
               this._chatModel.addMessage(this._chatMessageFactory.createInfoMessage(this._translator.getText(LangConstants.CHAT_MATCH_CHANNEL_AVAILABLE)));
               return;
            }
            if(channel.channelType == ClientChannelType.GENERAL && (selected == null || channel.lang == this._accountInformations.lang)) selected=channel;
         }
         if(selected != null) this._chatModel.selectActiveChannel(selected.channelType,selected.lang);
      }
   }
}
