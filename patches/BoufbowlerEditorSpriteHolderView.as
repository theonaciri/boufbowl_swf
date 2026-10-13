package com.ankamagames.boufbowl.client.premiumservice.boufbowlercustomisation.view
{
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerModel;
   import com.ankamagames.boufbowl.client.match.strategic.view.teampanel.BoufbowlerSpriteHolderView;
   import com.ankamagames.boufbowl.client.match.view.IBoufbowlerSpriteFactory;
   import com.ankamagames.boufbowl.client.club.view.IllustrationViewFactory;
   import com.ankamagames.boufbowl.client.club.view.BoufbowlerIllustrationView;
   import com.ankamagames.boufbowl.client.club.view.BoufbowlerPosingType;
   import com.ankamagames.boufbowl.resolution.display.animation.AnimationKey;

   public class BoufbowlerEditorSpriteHolderView extends BoufbowlerSpriteHolderView
   {
      private var _currentAnimationKey:AnimationKey;
      private var _illustrationFactory:IllustrationViewFactory;
      private var _heroPreview:BoufbowlerIllustrationView;

      public function BoufbowlerEditorSpriteHolderView(param1:IBoufbowlerSpriteFactory, param2:IllustrationViewFactory)
      {
         super(param1);
         _illustrationFactory = param2;
      }

      public function set currentAnimationKey(param1:AnimationKey) : void
      {
         _currentAnimationKey = param1;
      }

      override public function updateBoufbowler(param1:IBoufbowlerModel) : void
      {
         if(!param1.isUniqueCharacter)
         {
            super.updateBoufbowler(param1);
            return;
         }
         // Hero animation SWLs are absent from the supplied archive. Render
         // the genuine character artwork instead of requesting missing skins.
         removeBoufbowlerAnimation();
         if(_heroPreview == null)
            _heroPreview = _illustrationFactory.getBoufbowlerIllustration(BoufbowlerPosingType.DEFAULT,false);
         _heroPreview.update(param1);
         _heroPreview.scaleX = _heroPreview.scaleY = 0.30;
         addChild(_heroPreview);
      }

      override public function removeBoufbowlerAnimation() : void
      {
         if(_heroPreview != null && _heroPreview.parent == this)
            removeChild(_heroPreview);
         super.removeBoufbowlerAnimation();
      }

      override public function updateAnimation(param1:IBoufbowlerModel) : void
      {
         if(!param1.isUniqueCharacter) super.updateAnimation(param1);
      }

      override protected function getAnimation(param1:IBoufbowlerModel) : AnimationKey
      {
         return _currentAnimationKey;
      }

      override protected function getAngle(param1:IBoufbowlerModel) : Number
      {
         return 60;
      }
   }
}
