package com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.controller
{
   import com.ankamagames.boufbowl.client.application.messagebox.event.MessageBoxEvent;
   import com.ankamagames.boufbowl.client.club.model.ClubModel;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.model.BoufbowlerEditionModel;
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller.datavalidation.ClubDataValidator;
   import com.ankamagames.boufbowl.client.premiumservice.clubcustomisation.controller.datavalidation.ValidationResult;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.events.Event;
   import org.robotlegs.utilities.modular.mvcs.ModuleCommand;
   
   public class BoufbowlerCustomisationConfirmCommand extends ModuleCommand
   {
      
      public static const APPLY_BOUFBOWLER_CUSTOMISATION:String = "com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.controller.BoufbowlerCustomisationConfirmCommand.APPLY_BOUFBOWLER_CUSTOMISATION";
      
      private var _clubDataValidator:ClubDataValidator;
      
      private var _boufbowlerEdition:BoufbowlerEditionModel;
      
      private var _translator:ITranslator;
      
      private var _currentClub:ClubModel;
      
      public function BoufbowlerCustomisationConfirmCommand(param1:BoufbowlerEditionModel, param2:ITranslator, param3:ClubDataValidator, param4:ClubModel)
      {
         super();
         this._boufbowlerEdition = param1;
         this._translator = param2;
         this._clubDataValidator = param3;
         this._currentClub = param4;
      }
      
      override public function execute() : void
      {
         if(this.isValid())
         {
            dispatchToModules(MessageBoxEvent.infos(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode() ? "Save these changes to your server profile?" : "Apply these changes to the offline session? They will reset when you close the player.",this._translator.getText(LangConstants.PREMIUMSERVICE_CUSTOMISATION_APPLY_CONFIRMATION_YES),new Event(APPLY_BOUFBOWLER_CUSTOMISATION),this._translator.getText(LangConstants.PREMIUMSERVICE_CUSTOMISATION_APPLY_CONFIRMATION_NO)));
         }
      }
      
      private function isValid() : Boolean
      {
         var _loc1_:ValidationResult = this._clubDataValidator.isValidCustomizedClubBoufbowler(this._boufbowlerEdition.customizedBoufbowler,this._boufbowlerEdition.customizedClub,true);
         if(!_loc1_.isValid)
         {
            dispatchToModules(MessageBoxEvent.infos(_loc1_.errorMessage,this._translator.getText(LangConstants.OK)));
            return false;
         }
         return true;
      }
   }
}

