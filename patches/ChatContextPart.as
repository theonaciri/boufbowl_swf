package com.ankamagames.boufbowl.client.chat
{
   import com.ankamagames.boufbowl.client.chat.controller.channel.ChangeChannelRegisterCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.ChatErrorCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.ChatNameMenuOptionCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.CommitChannelRegistrationCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.CommitChannelUnregistrationCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.MuteClientCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.ReceiveChannelsConfigurationCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.ReceiveChannelsUnavailableCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.SelectActiveChannelCommand;
   import com.ankamagames.boufbowl.client.chat.controller.channel.ViewRequestActivableChannelsListCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.ChatLocalCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.ChatRemoteCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.ModerationResultCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.OpponentDisconnectedCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.PingResultCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.PushChatMessageCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.ReportSuccessCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.SpectatorJoinedCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.StatsResultCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.TimeResultCommand;
   import com.ankamagames.boufbowl.client.chat.controller.command.WhoisResultCommand;
   import com.ankamagames.boufbowl.client.chat.controller.connection.ChatConnectionClosedCommand;
   import com.ankamagames.boufbowl.client.chat.controller.connection.ChatConnectionErrorCommand;
   import com.ankamagames.boufbowl.client.chat.controller.connection.ChatConnectionOpenedCommand;
   import com.ankamagames.boufbowl.client.chat.controller.contextmenu.ChatContextualMenuBuilder;
   import com.ankamagames.boufbowl.client.chat.controller.message.ParseChatMessageCommand;
   import com.ankamagames.boufbowl.client.chat.controller.message.ReceiveChatMessageFromChannelCommand;
   import com.ankamagames.boufbowl.client.chat.controller.message.ReceiveChatMessageFromClientCommand;
   import com.ankamagames.boufbowl.client.chat.model.ChatModel;
   import com.ankamagames.boufbowl.client.chat.model.IChatModel;
   import com.ankamagames.boufbowl.client.chat.model.channel.ChannelInformationsFactory;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatChannelEvent;
   import com.ankamagames.boufbowl.client.chat.model.event.ChatParsedMessageEvent;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageFactory;
   import com.ankamagames.boufbowl.client.chat.model.message.ChatMessageParser;
   import com.ankamagames.boufbowl.client.chat.network.ChatMessageHandler;
   import com.ankamagames.boufbowl.client.chat.network.ChatMessageWrapper;
   import com.ankamagames.boufbowl.client.chat.network.ChatNetworkMessageFactory;
   import com.ankamagames.boufbowl.client.chat.network.ReferredLoginConnectionHandler;
   import com.ankamagames.boufbowl.client.chat.view.ChatMediator;
   import com.ankamagames.boufbowl.client.chat.view.ChatView;
   import com.ankamagames.boufbowl.client.chat.view.channel.ChannelNameFactory;
   import com.ankamagames.boufbowl.client.chat.view.event.ChannelEnableChangeEvent;
   import com.ankamagames.boufbowl.client.chat.view.event.ChannelSelectorEvent;
   import com.ankamagames.boufbowl.client.chat.view.event.ChatNameMenuEvent;
   import com.ankamagames.boufbowl.client.match.MatchMessageHandler;
   import com.ankamagames.boufbowl.client.network.LobbyMessageHandler;
   import com.ankamagames.boufbowl.client.network.SlaveServerInformation;
   import com.ankamagames.boufbowl.client.network.SlaverServerConnectionManager;
   import com.ankamagames.boufbowl.client.tutorial.characters.TutorialSpeechCharacters;
   import com.ankamagames.boufbowl.client.tutorial.characters.TutorialSpeechSkinFactory;
   import com.ankamagames.xgaming.chat.protocol.ChatMessage;
   import com.ankamagames.xgaming.chat.protocol.UnionProtocol;
   import com.ankamagames.xgaming.chat.protocol.XGamingWrapperMessage;
   import com.ankamagames.xgaming.net.channel.FixedLengthFrameDecoder;
   import com.ankamagames.xgaming.net.channel.FixedLengthFrameEncoder;
   import com.ankamagames.xgaming.net.channel.ProtobufAS3Decoder;
   import com.ankamagames.xgaming.net.channel.ProtogenAs3Encoder;
   import com.ankamagames.xgaming.net.channel.pipeline.ChannelPipeline;
   import com.ankamagames.xgaming.net.channel.pipeline.ChannelPipelineFactory;
   import com.ankamagames.xgaming.net.connection.Connection;
   import com.ankamagames.xgaming.utils.injection.AbstractContextPart;
   import com.ankamagames.xgaming.utils.protocol.NetworkEventDispatcher;
   import com.ankamagames.xgaming.utils.protocol.NetworkMessageEvent;
   import flash.events.ErrorEvent;
   import flash.events.Event;
   import flash.events.TextEvent;
   import flash.net.Socket;

   public class ChatContextPart extends AbstractContextPart
   {

      public static const CHAT_SERVER:String = "CHAT";

      private static const MAX_NET_FRAME_LENGTH:Number = 128 * 1024;

      public function ChatContextPart()
      {
         super();
      }

      override protected function configure() : void
      {
         this.mapTypes();
         this.mapCommands();
         this.configurePipeline();
      }

      private function mapTypes() : void
      {
         injector.mapSingleton(ChannelInformationsFactory);
         injector.mapSingleton(ChannelNameFactory);
         injector.mapSingleton(ChatContextualMenuBuilder);
         injector.mapClass(TutorialSpeechCharacters,TutorialSpeechCharacters);
         // The mediator synchronizes existing channel state when it is created.
         // Its model must be mapped before mapView can construct the mediator.
         injector.mapSingletonOf(IChatModel,ChatModel);
         injector.mapSingleton(ChatView);
         mediatorMap.mapView(ChatView,ChatMediator,null,false,false);
         mediatorMap.createMediator(injector.getInstance(ChatView));
         injector.mapClass(ChatMessageFactory,ChatMessageFactory);
         injector.mapClass(ChatMessageParser,ChatMessageParser);
         injector.mapClass(ChatNetworkMessageFactory,ChatNetworkMessageFactory);
         injector.mapClass(TutorialSpeechSkinFactory,TutorialSpeechSkinFactory);
      }

      private function mapCommands() : void
      {
         commandMap.mapEvent(ChatMessageHandler.EVT_CHAT_CONNECTION_OPENED,ChatConnectionOpenedCommand,Event);
         commandMap.mapEvent(ChatMessageHandler.EVT_CHAT_CONNECTION_CLOSED,ChatConnectionClosedCommand,Event);
         commandMap.mapEvent(ChatMessageHandler.EVT_CHANNEL_CHAT_ERROR,ChatErrorCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatMessageHandler.EVT_CHAT_CONNECTION_ERROR,ChatConnectionErrorCommand,ErrorEvent);
         commandMap.mapEvent(ChatMessageHandler.EVT_MESSAGE_FROM_CHANNEL,ReceiveChatMessageFromChannelCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatMessageHandler.EVT_MESSAGE_FROM_CLIENT,ReceiveChatMessageFromClientCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatMessageHandler.EVT_CLIENT_IS_MUTE,MuteClientCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatMessageHandler.EVT_REPORT_SUCCESS,ReportSuccessCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatView.EVT_TEXT_VALIDATED,ParseChatMessageCommand,TextEvent);
         commandMap.mapEvent(ChatView.EVT_CHANNEL_REGISTER_CHANGE,ChangeChannelRegisterCommand,ChannelEnableChangeEvent);
         commandMap.mapEvent(ChatView.EVT_REQUEST_ACTIVABLE_CHANNELS_LIST,ViewRequestActivableChannelsListCommand,Event);
         commandMap.mapEvent(ChatView.EVT_CHANNEL_SELECTED,SelectActiveChannelCommand,ChannelSelectorEvent);
         commandMap.mapEvent(ChatView.EVT_NAME_CLICKED,ChatNameMenuOptionCommand,ChatNameMenuEvent);
         commandMap.mapEvent(ChatMessageParser.EVT_PUSH_MESSAGE,PushChatMessageCommand,ChatParsedMessageEvent);
         commandMap.mapEvent(ChatMessageParser.EVT_LOCAL_COMMAND,ChatLocalCommand,ChatParsedMessageEvent);
         commandMap.mapEvent(ChatMessageParser.EVT_REMOTE_COMMAND,ChatRemoteCommand,ChatParsedMessageEvent);
         moduleCommandMap.mapEvent(LobbyMessageHandler.PING_RESULT,PingResultCommand,NetworkMessageEvent);
         moduleCommandMap.mapEvent(LobbyMessageHandler.TIME_RESULT,TimeResultCommand,NetworkMessageEvent);
         moduleCommandMap.mapEvent(LobbyMessageHandler.WHOIS_RESULT,WhoisResultCommand,NetworkMessageEvent);
         moduleCommandMap.mapEvent(LobbyMessageHandler.STATS_RESULT,StatsResultCommand,NetworkMessageEvent);
         moduleCommandMap.mapEvent(LobbyMessageHandler.MODERATION_RESULT,ModerationResultCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatMessageHandler.EVT_CHANNEL_AVAILABLE_NOTIFICATION,ReceiveChannelsConfigurationCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatMessageHandler.EVT_CHANNEL_UNAVAILABLE_NOTIFICATION,ReceiveChannelsUnavailableCommand,NetworkMessageEvent);
         commandMap.mapEvent(ChatModel.EVT_CHANNEL_REGISTERED,CommitChannelRegistrationCommand,ChatChannelEvent);
         commandMap.mapEvent(ChatModel.EVT_CHANNEL_UNREGISTERED,CommitChannelUnregistrationCommand,ChatChannelEvent);
         moduleCommandMap.mapEvent(MatchMessageHandler.OPPONENT_DISCONNECTED,OpponentDisconnectedCommand);
         moduleCommandMap.mapEvent(MatchMessageHandler.OPPONENT_RECONNECTED,OpponentDisconnectedCommand);
         moduleCommandMap.mapEvent(MatchMessageHandler.AWAITING_OPPONENT,OpponentDisconnectedCommand);
         moduleCommandMap.mapEvent(MatchMessageHandler.SPECTATOR_JOINED,SpectatorJoinedCommand,NetworkMessageEvent);
         moduleCommandMap.mapEvent(MatchMessageHandler.SPECTATOR_LEFT,SpectatorJoinedCommand,NetworkMessageEvent);
      }

      private function configurePipeline() : void
      {
         var _loc1_:ChannelPipeline = ChannelPipelineFactory.buildPipeline(new Connection(new Socket()));
         injector.mapSingleton(NetworkEventDispatcher,CHAT_SERVER);
         injector.mapValue(ChannelPipeline,_loc1_,CHAT_SERVER);
         injector.mapSingleton(ChatMessageHandler);
         var _loc2_:SlaverServerConnectionManager = injector.getInstance(SlaverServerConnectionManager);
         var _loc3_:SlaveServerInformation = new SlaveServerInformation(CHAT_SERVER,_loc1_);
         _loc2_.putSlaveServerInformation(CHAT_SERVER,_loc3_);
         _loc1_.addLast(new FixedLengthFrameDecoder(MAX_NET_FRAME_LENGTH));
         _loc1_.addLast(new ProtobufAS3Decoder(ChatMessage));
         _loc1_.addLast(injector.getInstance(ChatMessageHandler));
         _loc1_.addLast(new ReferredLoginConnectionHandler(_loc3_,XGamingWrapperMessage));
         _loc1_.addLast(new FixedLengthFrameEncoder());
         _loc1_.addLast(new ProtogenAs3Encoder());
         _loc1_.addLast(new ChatMessageWrapper(new UnionProtocol()));
      }
   }
}

