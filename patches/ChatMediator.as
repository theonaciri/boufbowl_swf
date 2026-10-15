package com.ankamagames.boufbowl.client.chat.view
{
   import com.ankamagames.boufbowl.client.application.mediator.BoufbowlMediator;
   import com.ankamagames.boufbowl.client.chat.controller.channel.ViewRequestActivableChannelsListCommand;
   import com.ankamagames.boufbowl.client.chat.controller.event.AvailableChannelsListEvent;
   import com.ankamagames.boufbowl.client.chat.model.ChatModel;
   import com.ankamagames.boufbowl.client.chat.model.IChatModel;
   import com.ankamagames.boufbowl.client.chat.model.channel.ChannelInformation;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatChannelEvent;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatMenuEvent;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatMessageEvent;
   import com.ankamagames.boufbowl.client.chat.view.event.ChannelEnableChangeEvent;
   import com.ankamagames.boufbowl.client.chat.view.event.ChatNameMenuEvent;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.events.Event;
   import flash.events.TextEvent;

   public class ChatMediator extends BoufbowlMediator
   {

      private var _view:ChatView;

      private var _translator:ITranslator;
      private var _chatModel:IChatModel;

      public function ChatMediator(param1:ChatView, param2:ITranslator, param3:IChatModel)
      {
         super();
         this._view = param1;
         this._translator = param2;
         this._chatModel = param3;
      }

      override public function onRegister() : void
      {
         super.onRegister();
         addContextListener(ChatModel.EVT_CHAT_MESSAGE_ADDED,this.chatMessageAddedHandler,ChatMessageEvent);
         addContextListener(ChatModel.EVT_AVAILABLE_CHANNEL_ADDED,this.availableChannelAddedHandler,ChatChannelEvent);
         addContextListener(ChatModel.EVT_AVAILABLE_CHANNEL_REMOVED,this.availableChannelRemovedHandler,ChatChannelEvent);
         addContextListener(ChatModel.EVT_CLEAR_AVAILABLE_CHANNELS,this.clearAvailableChannelsHandler,Event);
         addContextListener(ChatModel.EVT_CHANNEL_REGISTERED,this.channelRegisteredHandler,ChatChannelEvent);
         addContextListener(ChatModel.EVT_CHANNEL_UNREGISTERED,this.channelUnregisteredHandler,ChatChannelEvent);
         addContextListener(ViewRequestActivableChannelsListCommand.EVT_AVAILABLE_CHANNELS_LIST,this.availableChannelsListHandler,AvailableChannelsListEvent);
         addContextListener(ChatModel.EVT_ACTIVE_CHANNEL_SELECTED,this.activeChannelSelectedHandler,ChatChannelEvent);
         addContextListener(ChatModel.EVT_MESSAGES_CLEARED,this.messagesClearedHandler,Event);
         addContextListener(ChatMenuEvent.WHISPER_CHAT_EVENT,this.whisperNicknameHandler,ChatMenuEvent);
         addContextListener(ChatMenuEvent.COPY_NICKNAME_CHAT_EVENT,this.copyNicknameHandler);
         addViewListener(ChatView.EVT_TEXT_VALIDATED,dispatch,TextEvent);
         addViewListener(ChatView.EVT_CHANNEL_REGISTER_CHANGE,dispatch,ChannelEnableChangeEvent);
         addViewListener(ChatView.EVT_REQUEST_ACTIVABLE_CHANNELS_LIST,dispatch,Event);
         addViewListener(ChatView.EVT_CHANNEL_SELECTED,dispatch,Event);
         addViewListener(ChatView.EVT_NAME_CLICKED,this.chatNameClicked,Event);
         // The persistent model can receive channel configuration before a
         // recreated view registers its listeners (startup, reconnect, replay).
         var channels:IIterator = this._chatModel.getActivableChannels().getIterator();
         while(channels.hasNext())
         {
            var channel:ChannelInformation = channels.getNext();
            this._view.setAvailableChannel(channel,true);
            this._view.setRegisteredChannel(channel,channel.registered);
         }
         this.syncSelectedChannel();
      }

      private function syncSelectedChannel() : void
      {
         if(this._chatModel.activeChannel != null)
            this._view.setSelectedChannel(this._chatModel.activeChannel);
      }

      private function messagesClearedHandler(param1:Event) : void
      {
         this._view.clearMessages();
      }

      private function activeChannelSelectedHandler(param1:ChatChannelEvent) : void
      {
         this._view.setSelectedChannel(param1.channelInfos);
      }

      private function availableChannelsListHandler(param1:AvailableChannelsListEvent) : void
      {
         this._view.openAvailableChannelsList(param1.availableChannels);
      }

      private function availableChannelAddedHandler(param1:ChatChannelEvent) : void
      {
         this._view.setAvailableChannel(param1.channelInfos,true);
      }

      private function availableChannelRemovedHandler(param1:ChatChannelEvent) : void
      {
         this._view.setAvailableChannel(param1.channelInfos,false);
      }

      private function clearAvailableChannelsHandler(param1:Event) : void
      {
         this._view.clearAvailableChannels();
      }

      private function channelRegisteredHandler(param1:ChatChannelEvent) : void
      {
         this._view.setRegisteredChannel(param1.channelInfos,true);
         this._view.update(param1.messages);
      }

      private function channelUnregisteredHandler(param1:ChatChannelEvent) : void
      {
         this._view.setRegisteredChannel(param1.channelInfos,false);
         this._view.update(param1.messages);
      }

      private function chatMessageAddedHandler(param1:ChatMessageEvent) : void
      {
         this.syncSelectedChannel();
         this._view.addMessage(param1.message,true);
      }

      private function chatNameClicked(param1:ChatNameMenuEvent) : void
      {
         dispatch(param1);
      }

      private function whisperNicknameHandler(param1:ChatMenuEvent) : void
      {
         this._view.prepareWhisperNickname(param1.nickname);
      }

      private function copyNicknameHandler(param1:ChatMenuEvent) : void
      {
         this._view.insertNickname(param1.nickname);
      }
   }
}

