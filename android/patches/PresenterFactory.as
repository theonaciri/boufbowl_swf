package com.ankamagames.boufbowl.resolution.display.presenter
{
   import away3d.materials.BitmapFileMaterial;
   import away3d.primitives.Plane;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.boufbowl.resolution.display.camera.BoufbowlCamera;
   import com.ankamagames.boufbowl.resolution.display.model.IBall;
   import com.ankamagames.boufbowl.resolution.display.model.IBoufbowler;
   import com.ankamagames.boufbowl.resolution.display.model.IGrid;
   import com.ankamagames.boufbowl.resolution.display.model.Onomatopeia;
   import com.ankamagames.boufbowl.utils.ControlledMovieClipFromResource;
   import com.ankamagames.xgaming.utils.load.SwfRegistry;
   import flash.display.Sprite;
   
   public class PresenterFactory implements IPresenterFactory
   {
      
      private var _registry:SwfRegistry;
      
      private var _assetsConfig:IBoufbowlConfig;
      
      private var _camera:BoufbowlCamera;
      
      private const SPRITE_SCALE_FACTOR:Number = 3.5;
      
      public function PresenterFactory(param1:SwfRegistry, param2:IBoufbowlConfig, param3:BoufbowlCamera)
      {
         super();
         this._registry = param1;
         this._assetsConfig = param2;
         this._camera = param3;
      }
      
      public function createBoufbowler(param1:IBoufbowler) : IBoufbowlerPresenter
      {
         var _loc2_:ISpritePresenter = this.newMovieMaterialSpritePresenter(this.SPRITE_SCALE_FACTOR);
         return new BoufbowlerPresenter(param1,_loc2_,this._camera,this._registry);
      }
      
      public function createBall(param1:IBall) : BallPresenter
      {
         var _loc2_:ISpritePresenter = this.newMovieMaterialSpritePresenter(this.SPRITE_SCALE_FACTOR);
         var _loc3_:Sprite = param1.sprite.createSprite(this._registry);
         _loc2_.sprite = _loc3_;
         return new BallPresenter(param1,_loc2_);
      }
      
      public function createBallShadow(param1:IBall) : BallShadowPresenter
      {
         var _loc2_:ISpritePresenter = this.newMovieMaterialSpritePresenter(this.SPRITE_SCALE_FACTOR);
         _loc2_.sprite = param1.shadowSprite.createSprite(this._registry);
         return new BallShadowPresenter(param1,_loc2_);
      }
      
      public function createGrid(param1:IGrid) : GridPresenter
      {
         var _loc2_:Plane = new Plane();
         _loc2_.rotationY = 90;
         var _loc3_:BitmapFileMaterial = new BitmapFileMaterial("app:/assets/textures/grid/simple.png");
         _loc3_.smooth = true;
         _loc3_.repeat = true;
         _loc2_.material = _loc3_;
         return new GridPresenter(param1,_loc2_);
      }
      
      public function createOnomatopeia(param1:Onomatopeia) : OnomatopeiaPresenter
      {
         var _loc2_:ISpritePresenter = this.newMovieMaterialSpritePresenter(this.SPRITE_SCALE_FACTOR);
         var _loc3_:ControlledMovieClipFromResource = new ControlledMovieClipFromResource(param1.frameController,param1.name,this._registry,this._assetsConfig.onomatopoeiasFile);
         return new OnomatopeiaPresenter(param1,_loc3_,_loc2_);
      }
      
      private function newMovieMaterialSpritePresenter(param1:Number) : ISpritePresenter
      {
         return new MovieClipSpritePresenter(param1);
      }
   }
}

