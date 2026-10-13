package com.ankamagames.boufbowl.client.match.strategic.view
{
   import as3.collections.IList;
   import as3.collections.iterators.IIterator;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel;
   import com.ankamagames.boufbowl.protocol.BoufbowlerClass;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   
   public class ClassOrderTextComputer
   {
      
      private var _translator:ITranslator;
      
      public function ClassOrderTextComputer(param1:ITranslator)
      {
         super();
         this._translator = param1;
      }
      
      public function getTooltip(param1:IBoufbowlerInMatchModel) : String
      {
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode()) return com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverAbilityDescription(param1.boufbowlerClass);
         return this._translator.getText(LangConstants.ORDERPANEL_BTN_CLASS_TOOLTIP,this._translator.getEnumTranslation(LangConstants.CLASSES_ENUM,param1.boufbowlerClass),this._translator.getEnumTranslation(LangConstants.CLASSES_ORDER_NAME_ENUM,param1.boufbowlerClass),param1.attributes.classOrders,this._translator.getEnumTranslation(LangConstants.CLASSES_ORDER_TOOLTIP_DESC_ENUM,param1.boufbowlerClass));
      }
      
      public function getCombatLog(param1:IBoufbowlerInMatchModel, param2:IList) : String
      {
         if(com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverMode()) return param1.name + ": " + com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand.serverAbilityDescription(param1.boufbowlerClass);
         var _loc3_:String = this._translator.getText(LangConstants.COMBATLOG_CLASS_ORDER,param1.name,this._translator.getEnumTranslation(LangConstants.CLASSES_ENUM,param1.boufbowlerClass),this._translator.getEnumTranslation(LangConstants.CLASSES_ORDER_NAME_ENUM,param1.boufbowlerClass));
         if(param2.numItems == 0)
         {
            return _loc3_;
         }
         _loc3_ += "<br />";
         var _loc4_:Array = new Array();
         var _loc5_:IIterator = param2.getIterator();
         while(_loc5_.hasNext())
         {
            _loc4_.push(IBoufbowlerInMatchModel(_loc5_.getNext()).name);
         }
         var _loc6_:String = param1.boufbowlerClass != BoufbowlerClass.ZOBAL ? this._translator.getEnumTranslation(LangConstants.CLASSES_ORDER_COMBATLOG_DESC_ENUM,param1.boufbowlerClass) : this._translator.getEnumTranslation(LangConstants.CLASSES_ORDER_COMBATLOG_ZOBAL_DESC_ENUM,param1.currentZobalMask);
         return _loc3_ + this._translator.getText(param2.numItems == 1 ? LangConstants.COMBATLOG_CLASS_ORDER_TARGET : LangConstants.COMBATLOG_CLASS_ORDER_TARGETS,_loc4_.join(", "),_loc6_);
      }
   }
}

