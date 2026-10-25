package com.ankamagames.boufbowl.client.match.strategic.view.field.boufbowler
{
   import com.ankamagames.boufbowl.client.application.IColorScheme;
   import com.ankamagames.boufbowl.client.application.dragndrop.DragNDropStartWatcher;
   import com.ankamagames.boufbowl.client.application.dragndrop.DragNDropperMediator;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.application.tooltip.TargetTooltipView;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.match.IMatchColorScheme;
   import com.ankamagames.boufbowl.client.match.model.OrderModel;
   import com.ankamagames.boufbowl.client.match.strategic.event.StartDragEvent;
   import com.ankamagames.boufbowl.client.match.strategic.model.IBoufbowlerInMatchModel;
   import com.ankamagames.boufbowl.client.match.strategic.model.LinkedBoufbowlerData;
   import com.ankamagames.boufbowl.match.strategic.boufbowler.BoufbowlerFieldSprite;
   import com.ankamagames.boufbowl.protocol.BoufbowlerStatus;
   import com.ankamagames.boufbowl.protocol.Side;
   import com.ankamagames.xgaming.utils.display.DisplayListUtils;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.ankamagames.xgaming.utils.math.geom.Point2;
   import com.netease.protobuf.Int64;
   import flash.display.DisplayObject;
   import flash.display.Sprite;
   import flash.events.MouseEvent;
   import flash.events.Event;
   import flash.utils.getTimer;
   import flash.filters.GlowFilter;
   
   public class BoufbowlerFieldRepresentationView extends BoufbowlerFieldSprite
   {
      
      private var _cubeSpriteFactory:CubeSpriteFactory;
      
      private var _boufbowlerId:Int64;
      
      private var _boufbowlerSide:int;
      
      private var _onPlayerSide:Boolean;
      
      private var _colorScheme:IColorScheme;
      
      private var _matchColorScheme:IMatchColorScheme;
      
      private var _translator:ITranslator;
      
      private var _classSprite:Sprite;
      
      private var _halo:GlowFilter;
      
      private var _isKO:Boolean;
      
      private var _isWounded:Boolean;
      
      private var _dndStartWatcher:DragNDropStartWatcher;

      private var _hasBall:Boolean;

      private var _possessionStartedAt:int;
      
      public function BoufbowlerFieldRepresentationView(cubeSpriteFactory:CubeSpriteFactory, boufbowler:IBoufbowlerInMatchModel, colorScheme:IColorScheme, matchColorScheme:IMatchColorScheme, translator:ITranslator)
      {
         super();
         this._colorScheme = colorScheme;
         this._matchColorScheme = matchColorScheme;
         this._translator = translator;
         this._isKO = false;
         this._isWounded = false;
         this._cubeSpriteFactory = cubeSpriteFactory;
         this.init(boufbowler);
         addEventListener(Event.ADDED_TO_STAGE,this.possessionAddedToStage,false,0,true);
         addEventListener(Event.REMOVED_FROM_STAGE,this.possessionRemovedFromStage,false,0,true);
      }
      
      public function get boufbowlerId() : Int64
      {
         return this._boufbowlerId;
      }
      
      public function set hideHalo(param1:Boolean) : void
      {
         this._classSprite.filters = param1 ? [] : [this._halo];
      }
      
      public function get onPlayerSide() : Boolean
      {
         return this._onPlayerSide;
      }
      
      public function set hasBall(value:Boolean) : void
      {
         boufballFront.visible = value;
         boufballBack.visible = value;
         this._hasBall = value;
         removeEventListener(Event.ENTER_FRAME,this.updatePossessionAnimation);
         gotoAndStop(1);
         if(value)
         {
            DisplayListUtils.bringToFront(this);
            this._possessionStartedAt = getTimer();
            addEventListener(Event.ENTER_FRAME,this.updatePossessionAnimation,false,0,true);
         }
      }

      private function updatePossessionAnimation(event:Event) : void
      {
         // This 24-frame UI loop was authored for 25 FPS, independently of
         // the stage's render target. Its child indicator clips are static.
         var elapsed:int = Math.max(0,getTimer() - this._possessionStartedAt);
         var frame:int = 1 + Math.floor(elapsed * 25 / 1000) % totalFrames;
         if(currentFrame != frame) gotoAndStop(frame);
      }

      private function possessionAddedToStage(event:Event) : void
      {
         if(this._hasBall)
            addEventListener(Event.ENTER_FRAME,this.updatePossessionAnimation,false,0,true);
      }

      private function possessionRemovedFromStage(event:Event) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.updatePossessionAnimation);
      }

      public function set ko(param1:Boolean) : void
      {
         this._isKO = param1;
         this.setAlpha();
      }
      
      public function set wounded(param1:Boolean) : void
      {
         this._isWounded = param1;
         this.setAlpha();
      }
      
      public function blur() : void
      {
         this.setHaloFilter(this._matchColorScheme.getSideColor(this._boufbowlerSide));
      }
      
      public function updateBoufbowler(param1:IBoufbowlerInMatchModel, param2:Point2) : void
      {
         if(param1.id != this._boufbowlerId)
         {
            return;
         }
         x = param2.x;
         y = param2.y;
         this.hasBall = param1.hasBall;
         this.ko = param1.status == BoufbowlerStatus.KO;
         this.wounded = param1.status == BoufbowlerStatus.WOUNDED;
         visible = param1.onField;
         this.updateClassOrderIndicator(param1.order);
         this.updateTooltip(param1);
      }
      
      public function updateClassOrderIndicator(param1:OrderModel) : void
      {
         if(this._onPlayerSide)
         {
            classOrderIndicatorSprite.visible = this._onPlayerSide ? param1.classOrderActivated : false;
         }
      }
      
      public function updateTooltip(param1:IBoufbowlerInMatchModel) : void
      {
         var tooltipFunction:Function;
         var boufbowler:IBoufbowlerInMatchModel = param1;
         var tooltipContent:String = "<span fontWeight=\"bold\">" + boufbowler.name + "</span><br />";
         tooltipContent += "<span color=\"#FFFF00\">" + boufbowler.attributes.health + "/" + boufbowler.attributes.maxHealth + " " + this._translator.getText(LangConstants.FIELD_BOUFBOWLER_PV_TOOLTIP) + "</span>";
         if(boufbowler.status == BoufbowlerStatus.KO)
         {
            tooltipContent += "<br />" + this._translator.getText(LangConstants.FIELD_BOUFBOWLER_KO_TOOLTIP);
         }
         else if(boufbowler.status == BoufbowlerStatus.WOUNDED)
         {
            tooltipContent += "<br />" + this._translator.getText(LangConstants.FIELD_BOUFBOWLER_WOUNDED_TOOLTIP);
         }
         if(boufbowler.hasBall)
         {
            tooltipContent += "<br />" + this._translator.getText(LangConstants.FIELD_BOUFBOWLER_BALL_TOOLTIP);
         }
         if(boufbowler.order.targetType != OrderModel.TARGETING_NOTHING || boufbowler.order.classOrderActivated)
         {
            tooltipContent += "<br /><img source=\"[0]\" />";
         }
         tooltipFunction = function():DisplayObject
         {
            var _loc1_:TargetTooltipView = new TargetTooltipView(_colorScheme,_matchColorScheme,_cubeSpriteFactory);
            _loc1_.update(boufbowler);
            return _loc1_;
         };
         setTooltip(tooltipContent,Vector.<Function>([tooltipFunction]));
      }
      
      private function setAlpha() : void
      {
         alpha = this._isKO || this._isWounded ? this._matchColorScheme.koBoufbowlerAlpha : this._matchColorScheme.aliveBoufbowlerAlpha;
      }
      
      private function init(param1:IBoufbowlerInMatchModel) : void
      {
         this._boufbowlerId = param1.id;
         this._boufbowlerSide = param1.side;
         this._onPlayerSide = param1.onPlayerSide;
         buttonMode = useHandCursor = true;
         if(this._boufbowlerSide == Side.RIGHT)
         {
            scaleX *= -1;
         }
         this.hasBall = false;
         this._classSprite = this._cubeSpriteFactory.getBoufbowlerCubeSprite(param1);
         classOrderIndicatorSprite.visible = false;
         this._classSprite.scaleX *= 1.2;
         this._classSprite.scaleY = 1.2;
         spriteHolder.addChild(this._classSprite);
         this.setHaloFilter(this._matchColorScheme.getSideColor(this._boufbowlerSide));
         addEventListener(MouseEvent.CLICK,this.mouseClick,false,0,true);
         if(this._onPlayerSide)
         {
            this._dndStartWatcher = new DragNDropStartWatcher(this,this.requestStartDrag);
         }
      }
      
      private function requestStartDrag() : void
      {
         if(this._isWounded)
         {
            return;
         }
         dispatchEvent(new StartDragEvent(StartDragEvent.REQUEST,new LinkedBoufbowlerData(DragNDropperMediator.BOUFBOWLER,this._boufbowlerId)));
      }
      
      private function mouseClick(param1:MouseEvent) : void
      {
         if(this._onPlayerSide)
         {
            dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.MINE_BOUFBOWLER_CLICKED));
         }
         else
         {
            dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.HIS_BOUFBOWLER_CLICKED));
         }
      }
      
      private function setHaloFilter(param1:uint) : void
      {
         this._halo = new GlowFilter();
         this._halo.color = param1;
         this._halo.quality = 1;
         if(this._onPlayerSide)
         {
            this._halo.blurX = this._halo.blurY = 5;
            this._halo.strength = 6;
         }
         else
         {
            this._halo.blurX = this._halo.blurY = 3;
            this._halo.strength = 3;
         }
         this._classSprite.filters = [this._halo];
      }
   }
}

