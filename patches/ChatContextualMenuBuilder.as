package com.ankamagames.boufbowl.client.chat.controller.contextmenu
{
   import com.ankamagames.boufbowl.client.application.contextmenu.model.ContextMenuLineModel;
   import com.ankamagames.boufbowl.client.application.contextmenu.model.ContextMenuModel;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatMenuEvent;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatParsedMessageEvent;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageParser;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.ladder.event.DisplayLadderRequestEvent;
   import com.ankamagames.boufbowl.client.login.model.AccountInformations;
   import com.ankamagames.boufbowl.client.matchmaking.event.DisplayMatchCreationTypeEvent;
   import com.ankamagames.boufbowl.client.matchmaking.event.MatchSpectateEvent;
   import com.ankamagames.boufbowl.client.matchmaking.model.MatchCreationType;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.events.Event;
   
   public class ChatContextualMenuBuilder
   {
      
      private var _accountInformations:AccountInformations;
      
      private var _translator:ITranslator;
      
      public function ChatContextualMenuBuilder(param1:ITranslator, param2:AccountInformations)
      {
         super();
         this._translator = param1;
         this._accountInformations = param2;
      }
      
      public function buildMenuFromContext(param1:int, param2:String) : ContextMenuModel
      {
         var _loc3_:Boolean = param2 == this._accountInformations.nickname;
         var _loc4_:ContextMenuModel = new ContextMenuModel(param2);
         _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_COPY_NICKNAME),this.copyNickname(param2)));
         if(!_loc3_)
         {
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_WHISPER),this.whispNickname(param2)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_WHOIS),this.remoteCommand(param2,ChatMessageParser.WHOIS_COMMAND)));
         }
         if(param1 == ChatMenuContexts.IDLE)
         {
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_RANKING),this.ladderRequest(param2),true));
            if(!_loc3_)
            {
               _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_CHALLENGE),this.matchmakingChallengeRequest(param2),true));
               if(!com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode() || com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverCanSpectate(param2))
               {
                  _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_SPECTATE),this.matchSpectate(param2),true));
               }
            }
         }
         if(!_loc3_)
         {
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_IGNORE),this.localCommand(param2,ChatMessageParser.IGNORE_COMMAND)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_UNIGNORE),this.localCommand(param2,ChatMessageParser.UNIGNORE_COMMAND)));
         }
         if(!_loc3_ && (this._accountInformations.moderator || this._accountInformations.administrator))
         {
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_SHORT_MUTE),this.remoteCommand(param2,ChatMessageParser.SHORTMUTE_COMMAND)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_LONG_MUTE),this.remoteCommand(param2,ChatMessageParser.LONGMUTE_COMMAND)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_UNMUTE),this.remoteCommand(param2,ChatMessageParser.UNMUTE_COMMAND)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_REPORT),this.remoteCommand(param2,ChatMessageParser.REPORT_COMMAND)));
         }
         if(!_loc3_ && this._accountInformations.administrator)
         {
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_SHORT_BAN),this.remoteCommand(param2,ChatMessageParser.SHORTBAN_COMMAND)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_LONG_BAN),this.remoteCommand(param2,ChatMessageParser.LONGBAN_COMMAND)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_UNBAN),this.remoteCommand(param2,ChatMessageParser.UNBAN_COMMAND)));
            _loc4_.addLine(new ContextMenuLineModel(this._translator.getText(LangConstants.CHAT_KICK),this.remoteCommand(param2,ChatMessageParser.KICK_COMMAND)));
         }
         return _loc4_;
      }
      
      private function remoteCommand(param1:String, param2:String) : ChatParsedMessageEvent
      {
         return new ChatParsedMessageEvent(ChatMessageParser.EVT_REMOTE_COMMAND,param2,param1);
      }
      
      private function localCommand(param1:String, param2:String) : ChatParsedMessageEvent
      {
         return new ChatParsedMessageEvent(ChatMessageParser.EVT_LOCAL_COMMAND,param2,param1);
      }
      
      private function ladderRequest(param1:String) : Event
      {
         return new DisplayLadderRequestEvent(param1);
      }
      
      private function matchmakingChallengeRequest(param1:String) : Event
      {
         return new DisplayMatchCreationTypeEvent(MatchCreationType.CHALLENGE,param1);
      }
      
      private function matchSpectate(param1:String) : Event
      {
         return MatchSpectateEvent.withNickname(param1);
      }
      
      private function whispNickname(param1:String) : Event
      {
         return new ChatMenuEvent(ChatMenuEvent.WHISPER_CHAT_EVENT,param1);
      }
      
      private function copyNickname(param1:String) : Event
      {
         return new ChatMenuEvent(ChatMenuEvent.COPY_NICKNAME_CHAT_EVENT,param1);
      }
   }
}

