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
   import com.ankamagames.boufbowl.resolution.display.Constants;
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

      private var _hasBall:Boolean = false;

      private var _possessionRunning:Boolean = false;

      private var _possessionStartedAt:int = 0;

      private var _possessionElapsed:int = 0;

      public function BoufbowlerFieldRepresentationView(param1:CubeSpriteFactory, param2:IBoufbowlerInMatchModel, param3:IColorScheme, param4:IMatchColorScheme, param5:ITranslator)
      {
         super();
         this._colorScheme = param3;
         this._matchColorScheme = param4;
         this._translator = param5;
         this._isKO = false;
         this._isWounded = false;
         this._cubeSpriteFactory = param1;
         this.init(param2);
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

      public function set hasBall(hasBall:Boolean) : void
      {
         boufballFront.visible = hasBall;
         boufballBack.visible = hasBall;
         if(hasBall)
         {
            if(parent != null) DisplayListUtils.bringToFront(this);
            if(this._hasBall) return;
            this._hasBall = true;
            this._possessionElapsed = 0;
            gotoAndStop(1);
            addEventListener(Event.ADDED_TO_STAGE,this.startPossessionAnimation,false,0,true);
            addEventListener(Event.REMOVED_FROM_STAGE,this.pausePossessionAnimation,false,0,true);
            this.startPossessionAnimation();
         }
         else
         {
            this._hasBall = false;
            this._possessionRunning = false;
            this._possessionElapsed = 0;
            removeEventListener(Event.ENTER_FRAME,this.updatePossessionAnimation);
            removeEventListener(Event.ADDED_TO_STAGE,this.startPossessionAnimation);
            removeEventListener(Event.REMOVED_FROM_STAGE,this.pausePossessionAnimation);
            gotoAndStop(1);
         }
      }

      private function startPossessionAnimation(event:Event = null) : void
      {
         if(!this._hasBall || this._possessionRunning || stage == null) return;
         this._possessionStartedAt = getTimer();
         this._possessionRunning = true;
         addEventListener(Event.ENTER_FRAME,this.updatePossessionAnimation,false,0,true);
      }

      private function pausePossessionAnimation(event:Event) : void
      {
         if(!this._possessionRunning) return;
         this._possessionElapsed += getTimer() - this._possessionStartedAt;
         this._possessionRunning = false;
         removeEventListener(Event.ENTER_FRAME,this.updatePossessionAnimation);
      }

      private function updatePossessionAnimation(event:Event) : void
      {
         if(!this._possessionRunning) return;
         // The indicator is authored at 25 FPS; the stage rate controls redraws.
         var elapsed:int = this._possessionElapsed + getTimer() - this._possessionStartedAt;
         var frame:int = 1 + int(elapsed / Constants.DEFAULT_MILLISECONDS_PER_FRAME) % totalFrames;
         if(currentFrame != frame) gotoAndStop(frame);
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
