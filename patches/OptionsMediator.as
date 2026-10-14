package com.ankamagames.boufbowl.client.options.view
{
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.client.application.mediator.BoufbowlMediator;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.options.event.OptionsPropertyChanged;
   import com.ankamagames.boufbowl.client.options.event.SetOptionsEvent;
   import com.ankamagames.boufbowl.client.options.event.ShowOptionsEvent;
   import com.ankamagames.boufbowl.client.options.model.OptionsDescriptor;
   import com.ankamagames.boufbowl.client.options.model.OptionsProperties;
   import flash.events.Event;
   import flash.events.MouseEvent;
   
   public class OptionsMediator extends BoufbowlMediator
   {
      
      public static const LOGOUT_CLICKED:String = "com.ankamagames.boufbowl.client.options.view.OptionsMediator.LOGOUT_CLICKED";
      
      private var _view:OptionsView;
      
      public function OptionsMediator(param1:OptionsView)
      {
         super();
         this._view = param1;
      }
      
      override public function onRegister() : void
      {
         super.onRegister();
         addContextListener(OptionsPropertyChanged.EVENT,this.propertyChanged);
         eventMap.mapListener(this._view.closeButton,MouseEvent.CLICK,this.closeButtonClickHandler);
         eventMap.mapListener(this._view.disconnectButton,MouseEvent.CLICK,this.logoutButtonClickHandler);
      }
      
      private function propertyChanged(param1:OptionsPropertyChanged) : void
      {
         if(param1.property == OptionsProperties.DISPLAY)
         {
            if(param1.model.display)
            {
               this._view.show();
            }
            else
            {
               this._view.hide();
            }
            dispatch(new InterfaceSoundEvent(InterfaceSoundEvents.OPTIONS_CHECKBOX_CHANGED));
            return;
         }
         throw IllegalStateError("Unknown OptionsProperty " + param1.property);
      }
      
      private function closeButtonClickHandler(param1:MouseEvent) : void
      {
         this._view.saveLanguage();
         var _loc2_:OptionsDescriptor = new OptionsDescriptor(this._view.soundCheckbox.selected,this._view.soundMasterVolume.value,this._view.chronoCheckbox.selected,this._view.scene3dCheckbox.selected,this._view.statsCheckbox.selected,this._view.serverHost,parseInt(this._view.serverPort));
         dispatch(new InterfaceSoundEvent(InterfaceSoundEvents.OPTIONS_CLOSE_BUTTON_CLICKED));
         dispatchToModules(new SetOptionsEvent(_loc2_));
         dispatchToModules(new ShowOptionsEvent(false));
      }
      
      private function logoutButtonClickHandler(param1:MouseEvent) : void
      {
         dispatch(new InterfaceSoundEvent(InterfaceSoundEvents.OPTIONS_CLOSE_BUTTON_CLICKED));
         dispatchToModules(new ShowOptionsEvent(false));
         dispatchToModules(new Event(LOGOUT_CLICKED));
      }
   }
}

