package com.ankamagames.boufbowl.client.chat.controller.channel
{
   import com.ankamagames.boufbowl.client.application.IBoufbowlViewDisplayer;
   import com.ankamagames.boufbowl.client.application.contextmenu.event.DisplayContextMenuEvent;
   import com.ankamagames.boufbowl.client.application.contextmenu.model.ContextMenuModel;
   import com.ankamagames.boufbowl.client.chat.controller.contextmenu.ChatContextualMenuBuilder;
   import com.ankamagames.boufbowl.client.chat.controller.contextmenu.ChatMenuContexts;
   import com.ankamagames.boufbowl.client.chat.view.event.ChatNameMenuEvent;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class ChatNameMenuOptionCommand extends ModuleCommand
   {
      
      private var _triggerEvent:ChatNameMenuEvent;
      
      private var _contextMenuBuilder:ChatContextualMenuBuilder;
      
      private var _viewDisplayer:IBoufbowlViewDisplayer;
      
      public function ChatNameMenuOptionCommand(param1:ChatNameMenuEvent, param2:ChatContextualMenuBuilder, param3:IBoufbowlViewDisplayer)
      {
         super();
         this._triggerEvent = param1;
         this._contextMenuBuilder = param2;
         this._viewDisplayer = param3;
      }
      
      override public function execute() : void
      {
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode())
         {
            com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverPlayerLookup(this._triggerEvent.clientName,this.displayMenu);
         }
         else this.displayMenu();
      }
      private function displayMenu() : void
      {
         var _loc1_:ContextMenuModel = this._contextMenuBuilder.buildMenuFromContext(ChatMenuContexts.fromViewType(this._viewDisplayer.currentViewType),this._triggerEvent.clientName);
         var _loc2_:DisplayContextMenuEvent = new DisplayContextMenuEvent(this._triggerEvent.mouseX,this._triggerEvent.mouseY,_loc1_);
         dispatchToModules(_loc2_);
      }
   }
}

