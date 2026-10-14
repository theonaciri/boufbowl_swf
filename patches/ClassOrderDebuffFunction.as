package com.ankamagames.boufbowl.client.match.resolution.interactions
{
   import as3.collections.Map;
   import com.ankamagames.boufbowl.protocol.ClassOrderTarget;
   import com.ankamagames.boufbowl.resolution.display.script.CommonInteractionFunctions;
   import com.ankamagames.boufbowl.resolution.display.script.runner.IBoufbowlerReference;
   
   public class ClassOrderDebuffFunction extends CommonInteractionFunctions
   {
      
      private var _targetList:Array;
      
      public function ClassOrderDebuffFunction(param1:Array)
      {
         super(new Map());
         this._targetList = param1;
      }
      
      override public function buildNodes() : void
      {
         this.targetDebuff();
      }
      
      private function targetDebuff() : void
      {
         var _loc1_:ClassOrderTarget = null;
         var _loc2_:IBoufbowlerReference = null;
         for each(_loc1_ in this._targetList)
         {
            if(_loc1_.hasPostResolutionHitPointsDelta && _loc1_.postResolutionHitPointsDelta != 0)
            {
               _loc2_ = getBoufbowlerReference(_loc1_.boufbowlerId);
               _loc2_.addOnomatopeia(getHpFxByDelta(_loc1_.postResolutionHitPointsDelta));
            }
         }
         wait(2000);
      }
   }
}

