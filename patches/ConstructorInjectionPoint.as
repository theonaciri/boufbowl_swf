package org.swiftsuspenders.injectionpoints
{
   import flash.utils.describeType;
   import flash.utils.getDefinitionByName;
   import flash.utils.getQualifiedClassName;
   import org.swiftsuspenders.Injector;
   
   public class ConstructorInjectionPoint extends MethodInjectionPoint
   {
      
      public function ConstructorInjectionPoint(param1:XML, param2:Class, param3:Injector)
      {
         var node:XML = param1;
         var clazz:Class = param2;
         var injector:Injector = param3;
         if(node.parameter.(@type == "*").length() == node.parameter.@type.length())
         {
            this.createDummyInstance(node,clazz);
         }
         // Ruffle omits class-level metadata from describeType. Recover only
         // known named constructor arguments when reflection provides none.
         if(node.parent().metadata.(@name == "Inject").length() == 0)
         {
            var names:Array = constructorNames(getQualifiedClassName(clazz));
            if(names != null)
            {
               var metadata:XML = <metadata name="Inject"/>;
               for each(var injectionName:String in names)
               {
                  var argument:XML = <arg key="name"/>;
                  argument.@value = injectionName;
                  metadata.appendChild(argument);
               }
               node.parent().appendChild(metadata);
            }
         }
         super(node,injector);
      }
      
      override public function applyInjection(param1:Object, param2:Injector) : Object
      {
         var _loc3_:Array = gatherParameterValues(param1,param2);
         switch(_loc3_.length)
         {
            case 0:
               return new param1();
            case 1:
               return new param1(_loc3_[0]);
            case 2:
               return new param1(_loc3_[0],_loc3_[1]);
            case 3:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2]);
            case 4:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2],_loc3_[3]);
            case 5:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2],_loc3_[3],_loc3_[4]);
            case 6:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2],_loc3_[3],_loc3_[4],_loc3_[5]);
            case 7:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2],_loc3_[3],_loc3_[4],_loc3_[5],_loc3_[6]);
            case 8:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2],_loc3_[3],_loc3_[4],_loc3_[5],_loc3_[6],_loc3_[7]);
            case 9:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2],_loc3_[3],_loc3_[4],_loc3_[5],_loc3_[6],_loc3_[7],_loc3_[8]);
            case 10:
               return new param1(_loc3_[0],_loc3_[1],_loc3_[2],_loc3_[3],_loc3_[4],_loc3_[5],_loc3_[6],_loc3_[7],_loc3_[8],_loc3_[9]);
            default:
               return null;
         }
      }
      
      override protected function initializeInjection(param1:XML, param2:Injector) : void
      {
         var nameArgs:XMLList = null;
         var node:XML = param1;
         var injector:Injector = param2;
         nameArgs = node.parent().metadata.(@name == "Inject").arg.(@key == "name");
         methodName = "constructor";
         gatherParameters(node,nameArgs,injector);
      }
      
      // Names and empty positional entries recovered from the shipped SWF
      // class traits, including metadata on the replacement client classes.
      private static function constructorNames(className:String) : Array
      {
         switch(className)
         {
            case "com.ankamagames.boufbowl.client.application.replay.controller::ProcessCommand": return ["LOBBY", "MATCH"];
            case "com.ankamagames.boufbowl.client.application::BoufbowlViewDisplayer": return ["", "viewDescriptors"];
            case "com.ankamagames.boufbowl.client.chat.controller.channel::CommitChannelRegistrationCommand": return ["", "CHAT"];
            case "com.ankamagames.boufbowl.client.chat.controller.channel::CommitChannelUnregistrationCommand": return ["", "CHAT"];
            case "com.ankamagames.boufbowl.client.chat.controller.channel::ReceiveChannelsUnavailableCommand": return ["", "", "", "CHAT"];
            case "com.ankamagames.boufbowl.client.chat.controller.command::ChatRemoteCommand": return ["LOBBY", "CHAT"];
            case "com.ankamagames.boufbowl.client.chat.controller.command::PushChatMessageCommand": return ["", "", "CHAT"];
            case "com.ankamagames.boufbowl.client.chat.controller.connection::ChatConnectionClosedCommand": return ["", "CHAT"];
            case "com.ankamagames.boufbowl.client.chat.controller.connection::ChatConnectionErrorCommand": return ["", "CHAT"];
            case "com.ankamagames.boufbowl.client.chat.network::ChatMessageHandler": return ["CHAT"];
            case "com.ankamagames.boufbowl.client.clubselection.controller::SendClubSelectionCommand": return ["", "", "", "", "", "LOBBY"];
            case "com.ankamagames.boufbowl.client.facebook.controller::LinkFacebookAccountCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.ladder.controller::LadderByLeagueRequestCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.ladder.controller::LadderByNickRequestCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.login.controller::AutoConnectCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.login.controller::LoginChannelErrorCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.login.controller::LoginChannelOpenedCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.login.controller::LoginCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.login.controller::LoginLobbyChallengeCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.login.controller::SendNicknameCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.login.controller::VersionCheckCommand": return ["", "", "LOBBY"];
            case "com.ankamagames.boufbowl.client.match.controller::ConfirmSurrenderAndCloseConnectionCommand": return ["", "MATCH"];
            case "com.ankamagames.boufbowl.client.match.controller::MatchChannelClosedCommand": return ["MATCH", "LOBBY"];
            case "com.ankamagames.boufbowl.client.match.controller::MatchChannelErrorCommand": return ["MATCH", "LOBBY"];
            case "com.ankamagames.boufbowl.client.match.controller::PhaseEndCommand": return ["", "MATCH"];
            case "com.ankamagames.boufbowl.client.match.controller::ScriptEndedCommand": return ["", "MATCH"];
            case "com.ankamagames.boufbowl.client.match.controller::StopSpectatingCommand": return ["MATCH"];
            case "com.ankamagames.boufbowl.client.match.controller::SurrenderCommand": return ["", "MATCH"];
            case "com.ankamagames.boufbowl.client.match.resolution.view::ResolutionView": return ["", "scene-ui-view"];
            case "com.ankamagames.boufbowl.client.match.strategic.model.grid::GridModel": return ["grid-width", "grid-height"];
            case "com.ankamagames.boufbowl.client.match.strategic.view::GridViewCoordConverter": return ["grid-cell-width", "grid-cell-height"];
            case "com.ankamagames.boufbowl.client.match::InGameSetup": return ["matchViewBundle"];
            case "com.ankamagames.boufbowl.client.match::MatchMessageHandler": return ["", "MATCH"];
            case "com.ankamagames.boufbowl.client.match::RandomMusicChooser": return ["strategicMusicList", "resolutionMusicList"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::AbandonChallengeCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::AcceptChallengeCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::CancelMatchRequestCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::ChallengeProposalCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::CreateChallengeCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::ReceiveTournamentClosedCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::RefreshTournamentsDatasCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::RequestRandomMatchCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::RequestRunningTournamentMatchesRequestCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::RequestTournamentLadderCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::RequestTournamentMatchCommnand": return ["", "", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::RequestTournamentsDatasCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.matchmaking.controller::SendMatchSpectateRequestCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.network.controller::CloseConnectionCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.network::LobbyMessageHandler": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.network::LobbyXGamingMessageHandler": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.controller::SendBoufbowlerCustomisationChangeCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.model::BoufbowlerEditionModel": return ["displayableAnimations"];
            case "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller::SendClubCustomisationChangeCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.premiumservice.common.controller::CustomisationRefusedCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.premiumservice.common.controller::CustomisationSessionRequestCommand": return ["", "LOBBY"];
            case "com.ankamagames.boufbowl.client.premiumservice.common.controller::QuitCustomisationCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.client.premiumservice.common.controller::RefreshPremiumContentCommand": return ["LOBBY"];
            case "com.ankamagames.boufbowl.resolution.display.presenter::UIPresenter": return ["", "scene-ui-view"];
            case "com.ankamagames.xgaming.audio.controller::AudioEventController": return ["", "interfaceSoundMap"];
         }
         return null;
      }

      private function createDummyInstance(param1:XML, param2:Class) : void
      {
         var constructorNode:XML = param1;
         var clazz:Class = param2;
         try
         {
            switch(constructorNode.children().length())
            {
               case 0:
                  new clazz();
                  break;
               case 1:
                  new clazz(null);
                  break;
               case 2:
                  new clazz(null,null);
                  break;
               case 3:
                  new clazz(null,null,null);
                  break;
               case 4:
                  new clazz(null,null,null,null);
                  break;
               case 5:
                  new clazz(null,null,null,null,null);
                  break;
               case 6:
                  new clazz(null,null,null,null,null,null);
                  break;
               case 7:
                  new clazz(null,null,null,null,null,null,null);
                  break;
               case 8:
                  new clazz(null,null,null,null,null,null,null,null);
                  break;
               case 9:
                  new clazz(null,null,null,null,null,null,null,null,null);
                  break;
               case 10:
                  new clazz(null,null,null,null,null,null,null,null,null,null);
            }
         }
         catch(error:Error)
         {
            trace(error);
         }
         constructorNode.setChildren(describeType(clazz).factory.constructor[0].children());
      }
   }
}

