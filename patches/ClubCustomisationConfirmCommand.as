package com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller
{
   import com.ankamagames.boufbowl.client.application.messagebox.event.MessageBoxEvent;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller.datavalidation.ClubDataValidator;
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller.datavalidation.ValidationResult;
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.model.ClubEditionModel;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.events.Event;
   import flash.events.TextEvent;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class ClubCustomisationConfirmCommand extends ModuleCommand
   {
      
      public static const SEND_CLUB_CUSTOMISATION:String = "com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller.ClubCustomisationConfirmCommand.SEND_CLUB_CUSTOMISATION";
      
      private var _clubDataValidator:ClubDataValidator;
      
      private var _clubEdition:ClubEditionModel;
      
      private var _translator:ITranslator;
      
      private var _event:TextEvent;
      
      private var _currentClub:ClubModel;
      
      public function ClubCustomisationConfirmCommand(param1:ClubEditionModel, param2:ITranslator, param3:TextEvent, param4:ClubDataValidator, param5:ClubModel)
      {
         super();
         this._clubEdition = param1;
         this._translator = param2;
         this._event = param3;
         this._clubDataValidator = param4;
         this._currentClub = param5;
      }
      
      override public function execute() : void
      {
         this._clubEdition.clubName = this._event.text;
         if(this.isValid())
         {
            dispatchToModules(MessageBoxEvent.infos("Apply these changes to the offline session? They will reset when you close the player.",this._translator.getText(LangConstants.PREMIUMSERVICE_CUSTOMISATION_APPLY_CONFIRMATION_YES),new Event(SEND_CLUB_CUSTOMISATION),this._translator.getText(LangConstants.PREMIUMSERVICE_CUSTOMISATION_APPLY_CONFIRMATION_NO)));
         }
      }
      
      private function isValid() : Boolean
      {
         var _loc1_:ValidationResult = this._clubDataValidator.isValidFullCustomizedClub(this._clubEdition,this._currentClub);
         if(!_loc1_.isValid)
         {
            dispatchToModules(MessageBoxEvent.infos(_loc1_.errorMessage,this._translator.getText(LangConstants.OK)));
            return false;
         }
         return true;
      }
   }
}

