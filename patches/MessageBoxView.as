package com.ankamagames.boufbowl.client.application.messagebox.view
{
   import com.ankamagames.boufbowl.client.application.IColorScheme;
   import com.ankamagames.boufbowl.ui.components.MessageBoxUI;
   import flash.events.Event;
   import flash.text.StyleSheet;
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;

   public class MessageBoxView extends MessageBoxUI
   {

      private var _colorScheme:IColorScheme;

      private var _firstButtonEvent:Event;

      private var _secondButtonEvent:Event;

      public function MessageBoxView(param1:IColorScheme)
      {
         super();
         this._colorScheme = param1;
         this.init();
      }

      public function get firstButtonEvent() : Event
      {
         return this._firstButtonEvent;
      }

      public function get secondButtonEvent() : Event
      {
         return this._secondButtonEvent;
      }

      public function update(param1:Boolean, param2:String, param3:String, param4:Event, param5:String = null, param6:Event = null) : void
      {
         if(param1) StartUpApplicationCommand.dismissServerPanel();
         visible = param1;
         internalUpdate(param2,param3,param5);
         this._firstButtonEvent = param4;
         this._secondButtonEvent = param6;
      }

      private function init() : void
      {
         visible = false;
         var _loc1_:StyleSheet = new StyleSheet();
         _loc1_.setStyle("a",{"color":"#" + this._colorScheme.messageBoxLinkColor.toString(16)});
         _loc1_.setStyle("a:hover",{"color":"#" + this._colorScheme.messageBoxLinkHoverColor.toString(16)});
         setStyleSheet(_loc1_);
      }
   }
}
