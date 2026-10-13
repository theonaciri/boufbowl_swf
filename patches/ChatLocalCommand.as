package com.ankamagames.boufbowl.client.chat.controller.command
{
   import com.ankamagames.boufbowl.client.chat.model.IChatModel;
   import com.ankamagames.boufbowl.client.chat.model.channel.ClientChannelType;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatParsedMessageEvent;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageData;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageFactory;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageParser;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.i18n.Languages;
   import com.ankamagames.boufbowl.client.login.model.AccountInformations;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.system.Capabilities;
   import org.robotlegs.mvcs.Command;
   
   public class ChatLocalCommand extends Command
   {
      
      private var _accountInformation:AccountInformations;
      
      private var _chatModel:IChatModel;
      
      private var _triggerEvent:ChatParsedMessageEvent;
      
      private var _chatMessageFactory:ChatMessageFactory;
      
      private var _translator:ITranslator;
      
      private var _config:IBoufbowlConfig;
      
      public function ChatLocalCommand(param1:ChatParsedMessageEvent, param2:IChatModel, param3:ChatMessageFactory, param4:ITranslator, param5:IBoufbowlConfig, param6:AccountInformations)
      {
         super();
         this._chatMessageFactory = param3;
         this._triggerEvent = param1;
         this._chatModel = param2;
         this._translator = param4;
         this._config = param5;
         this._accountInformation = param6;
      }
      
      override public function execute() : void
      {
         switch(this._triggerEvent.command)
         {
            case ChatMessageParser.UNKNOWN_COMMAND:
               this.unknownCommand();
               break;
            case ChatMessageParser.AIDE_COMMAND:
            case ChatMessageParser.HELP_COMMAND:
            case ChatMessageParser.AYUDA_COMMAND:
            case ChatMessageParser.HILFE_COMMAND:
            case ChatMessageParser.HELP2_COMMAND:
               this.helpCommand();
               break;
            case ChatMessageParser.VERSION_COMMAND:
               this.versionDisplayCommand();
               break;
            case ChatMessageParser.CLEAR_COMMAND:
               this.clearCommand();
               break;
            case ChatMessageParser.IGNORE_COMMAND:
               if(this._triggerEvent.param == null)
               {
                  return;
               }
               this.ignoreCommand(this._triggerEvent.param);
               break;
            case ChatMessageParser.UNIGNORE_COMMAND:
               if(this._triggerEvent.param == null)
               {
                  return;
               }
               this.unignoreCommand(this._triggerEvent.param);
               break;
            case ChatMessageParser.JOIN_COMMAND:
               if(this._triggerEvent.param == null)
               {
                  return;
               }
               this.joinGeneralChatChannel(Languages.getValidLanguage(this._triggerEvent.param));
               break;
            case ChatMessageParser.PART_COMMAND:
               if(this._triggerEvent.param == null)
               {
                  return;
               }
               this.partGeneralChatChannel(Languages.getValidLanguage(this._triggerEvent.param));
         }
      }
      
      private function unknownCommand() : void
      {
         var _loc1_:ChatMessageData = this._chatMessageFactory.createErrorMessage(this._translator.getText(LangConstants.CHAT_ERROR_UNKNOWN_COMMAND,ChatMessageParser.PREFIX_COMMAND + this._triggerEvent.param));
         this._chatModel.addMessage(_loc1_);
      }
      
      private function helpCommand() : void
      {
         var _loc4_:ChatMessageData = null;
         var _loc1_:String = this._translator.getText(LangConstants.CHAT_HELP_MESSAGE);
         var _loc2_:Array = _loc1_.split("\n");
         if(_loc2_ == null || _loc2_.length == 0)
         {
            return;
         }
         var _loc3_:String = _loc2_.shift();
         while(_loc3_ != null)
         {
            _loc4_ = this._chatMessageFactory.createInfoMessage(_loc3_);
            this._chatModel.addMessage(_loc4_);
            _loc3_ = _loc2_.shift();
         }
      }
      
      private function versionDisplayCommand() : void
      {
         var _loc1_:String = "Boufbowl Client : " + this._config.version;
         var _loc2_:ChatMessageData = this._chatMessageFactory.createInfoMessage(_loc1_);
         this._chatModel.addMessage(_loc2_);
         _loc1_ = "Flash Player : " + Capabilities.version;
         if(Capabilities.isDebugger)
         {
            _loc1_ += " (debug)";
         }
         _loc2_ = this._chatMessageFactory.createInfoMessage(_loc1_);
         this._chatModel.addMessage(_loc2_);
      }
      
      private function clearCommand() : void
      {
         this._chatModel.clearMessages();
      }
      
      private function ignoreCommand(param1:String) : void
      {
         if(param1.toLowerCase() == this._accountInformation.nickname.toLowerCase())
         {
            return;
         }
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode()) { com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverSetBlock(param1,true); return; }
         this._chatModel.ignoreUser(param1);
         var _loc2_:String = this._translator.getText(LangConstants.CHAT_IGNORED_USER,param1);
         var _loc3_:ChatMessageData = this._chatMessageFactory.createInfoMessage(_loc2_);
         this._chatModel.addMessage(_loc3_);
      }
      
      private function unignoreCommand(param1:String) : void
      {
         if(param1.toLowerCase() == this._accountInformation.nickname.toLowerCase())
         {
            return;
         }
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode()) { com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverSetBlock(param1,false); return; }
         this._chatModel.unignoreUser(param1);
         var _loc2_:String = this._translator.getText(LangConstants.CHAT_UNIGNORED_USER,param1);
         var _loc3_:ChatMessageData = this._chatMessageFactory.createInfoMessage(_loc2_);
         this._chatModel.addMessage(_loc3_);
      }
      
      private function joinGeneralChatChannel(param1:String) : void
      {
         this._chatModel.registerToChannel(ClientChannelType.GENERAL,param1);
         this._chatModel.savePreferredChannels();
      }
      
      private function partGeneralChatChannel(param1:String) : void
      {
         this._chatModel.unregisterFromChannel(ClientChannelType.GENERAL,param1);
         this._chatModel.savePreferredChannels();
      }
   }
}

