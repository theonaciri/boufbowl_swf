package com.ankamagames.boufbowl.client.options.view
{
   import as3.collections.iterators.IMapIterator;
   import com.ankamagames.boufbowl.client.ui.Slider;
   import com.ankamagames.xgaming.audio.controller.AbstractTracksController;
   import com.ankamagames.boufbowl.client.application.IColorScheme;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvent;
   import com.ankamagames.boufbowl.client.application.sound.event.InterfaceSoundEvents;
   import com.ankamagames.boufbowl.client.components.options.OptionsUI;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.config.IBoufbowlConfig;
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import flash.display.DisplayObject;
   import flash.display.Sprite;
   import flash.geom.Point;
   import flash.net.SharedObject;
   import flash.text.TextField;
   import flash.text.TextFormat;
   import flash.events.MouseEvent;
   import flash.system.Capabilities;
   
   public class OptionsView extends OptionsUI
   {
      
      private var _volumeRow:Sprite;
      private var _fxVolume:Slider;
      private var _musicVolume:Slider;
      private var _languageRow:Sprite;
      private var _languageButton:Sprite;
      private var _languageValue:TextField;
      private var _languageLabel:TextField;
      private var _languageHint:TextField;
      private var _selectedLanguage:String;
      private var _frameRateRow:Sprite;
      private var _frameRateTrack:Sprite;
      private var _frameRateThumb:Sprite;
      private var _frameRateValue:TextField;
      private var _frameRateLabel:TextField;
      private var _frameRateHint:TextField;
      private var _frameRateTarget:Number = 60;
      private var _frameRateDragging:Boolean = false;
      private var _languageCodes:Array=["fr","en","de","es"];
      private var _languageNames:Array=["Français","English","Deutsch","Español"];
      private var _config:IBoufbowlConfig;
      
      private var _translator:ITranslator;
      
      private var _colorScheme:IColorScheme;
      
      private const CONTAINER_SUFFIX:String = "Container";
      
      public function OptionsView(param1:ITranslator, param2:IBoufbowlConfig, param3:IColorScheme)
      {
         super();
         this._config = param2;
         this._translator = param1;
         this._colorScheme = param3;
         this.init();
      }
      
      public function show() : void
      {
         this._fxVolume.value = AbstractTracksController.fxVolume;
         this._musicVolume.value = AbstractTracksController.musicVolume;
         this.updateLanguageChoice();
         this.updateFrameRateChoice();
         this.layoutOptions();
         soundCheckbox.selected = this._config.soundEnabled;
         soundMasterVolume.value = this._config.soundMasterVolume;
         serverHost = this._config.serverHost;
         serverPort = this._config.serverPort.toString();
         statsCheckbox.selected = this._config.showStats;
         chronoCheckbox.selected = this._config.chronoEnabled;
         scene3dCheckbox.selected = this._config.activate3DScene;
         visible = true;
      }
      
      public function hide() : void
      {
         visible = false;
      }
      
      private function init() : void
      {
         this.hide();
         this.initUI();
         this.initTexts();
         this.initLanguageChoice();
         this.initFrameRateChoice();
         this.initVolumeSliders();
      }
      
      private function initUI() : void
      {
         title = this._translator.getText(LangConstants.OPTIONS_TITLE);
         soundCheckbox.boxColor = Color3.fromRgbUInt(this._colorScheme.checkboxBoxColor);
         soundCheckbox.tickColor = Color3.fromRgbUInt(this._colorScheme.checkboxTickColor);
         soundMasterVolume.thumbColor = this._colorScheme.checkboxBoxColor;
         statsCheckbox.boxColor = Color3.fromRgbUInt(this._colorScheme.checkboxBoxColor);
         statsCheckbox.tickColor = Color3.fromRgbUInt(this._colorScheme.checkboxTickColor);
         chronoCheckbox.boxColor = Color3.fromRgbUInt(this._colorScheme.checkboxBoxColor);
         chronoCheckbox.tickColor = Color3.fromRgbUInt(this._colorScheme.checkboxTickColor);
         scene3dCheckbox.boxColor = Color3.fromRgbUInt(this._colorScheme.checkboxBoxColor);
         scene3dCheckbox.tickColor = Color3.fromRgbUInt(this._colorScheme.checkboxTickColor);
         soundCheckbox.addEventListener(MouseEvent.CLICK,this.checkboxClickHandler);
         statsCheckbox.addEventListener(MouseEvent.CLICK,this.checkboxClickHandler);
         chronoCheckbox.addEventListener(MouseEvent.CLICK,this.checkboxClickHandler);
         scene3dCheckbox.addEventListener(MouseEvent.CLICK,this.checkboxClickHandler);
      }
      
      private function initTexts() : void
      {
         soundCheckbox.componentLabel = this._translator.getText(LangConstants.OPTIONS_SOUND_MASTER_VOLUME_ENABLED);
         serverTitle = this._translator.getText(LangConstants.OPTIONS_SERVER);
         statsCheckbox.componentLabel = this._translator.getText(LangConstants.OPTIONS_SHOW_STATS);
         chronoCheckbox.componentLabel = this._translator.getText(LangConstants.OPTIONS_CHRONO_ENABLED);
         scene3dCheckbox.componentLabel = this._translator.getText(LangConstants.OPTIONS_SCENE3D_ENABLED);
         closeButton.setTooltip(this._translator.getText(LangConstants.CLOSE));
         disconnectButton.componentLabel = this._translator.getText(LangConstants.LOGOUT);
         shortcutsTitle = this._translator.getText(LangConstants.OPTIONS_SHORTCUTS_TITLE);
         shortcutsExplanation = this._translator.getText(LangConstants.OPTIONS_SHORTCUTS_EXPLANATION);
         versionInfos = this.computeVersionInfos();
      }
      
      private function languageText(parent:Sprite, text:String, x:Number, y:Number, width:Number) : TextField
      {
         var field:TextField=new TextField();
         field.defaultTextFormat=new TextFormat("_sans",12,0x333333);
         field.text=text; field.x=x; field.y=y; field.width=width; field.height=22;
         field.selectable=false; field.mouseEnabled=false; parent.addChild(field);
         return field;
      }

      private function initVolumeSliders() : void
      {
         this._volumeRow = new Sprite();
         addChild(this._volumeRow);
         var labels:Object = {fr:["Volume des effets", "Volume de la musique"],en:["FX volume", "Music volume"],de:["Effektlautstärke", "Musiklautstärke"],es:["Volumen de efectos", "Volumen de música"]};
         var text:Array = labels[this._translator.language] || labels.en;
         this._fxVolume = this.createVolumeSlider(String(text[0]),0,"fxVolume");
         this._musicVolume = this.createVolumeSlider(String(text[1]),35,"musicVolume");
      }

      private function createVolumeSlider(label:String, rowY:Number, sliderName:String) : Slider
      {
         this.languageText(this._volumeRow,label,0,rowY+2,185);
         var slider:Slider = new Slider();
         slider.name = sliderName;
         slider.x = soundMasterVolume.x;
         slider.y = rowY + 10;
         slider.width = soundMasterVolume.width;
         slider.thumbColor = this._colorScheme.checkboxBoxColor;
         this._volumeRow.addChild(slider);
         return slider;
      }

      public function saveAudioVolumes() : void
      {
         AbstractTracksController.saveCategoryVolumes(this._fxVolume.value,this._musicVolume.value);
      }

      private function initLanguageChoice() : void
      {
         this._languageRow=new Sprite(); addChild(this._languageRow);
         this._languageLabel=this.languageText(this._languageRow,"",0,3,125);
         this._languageButton=new Sprite(); this._languageButton.x=130; this._languageButton.buttonMode=true;
         this._languageButton.graphics.beginFill(0xe5dfb2); this._languageButton.graphics.drawRoundRect(0,0,180,27,6); this._languageButton.graphics.endFill();
         this._languageRow.addChild(this._languageButton);
         this._languageValue=this.languageText(this._languageButton,"",8,3,164);
         this._languageHint=this.languageText(this._languageRow,"",0,32,350);
         this._languageHint.wordWrap=true; this._languageHint.height=35;
         this._languageButton.addEventListener(MouseEvent.CLICK,function(event:MouseEvent):void {
            var index:int=_languageCodes.indexOf(_selectedLanguage);
            _selectedLanguage=String(_languageCodes[(index+1)%_languageCodes.length]);
            _languageValue.text=String(_languageNames[_languageCodes.indexOf(_selectedLanguage)]) + " >";
         });
      }

      private function updateLanguageChoice() : void
      {
         var saved:SharedObject=SharedObject.getLocal("BoufbowlPreferences","/");
         this._selectedLanguage=String(saved.data.language);
         if(this._languageCodes.indexOf(this._selectedLanguage)<0) this._selectedLanguage=this._translator.language;
         this._languageValue.text=String(this._languageNames[this._languageCodes.indexOf(this._selectedLanguage)]) + " >";
         var labels:Object={fr:["Langue du jeu","Fermez les options pour enregistrer. Redémarrez le jeu pour appliquer."],en:["Game language","Close settings to save. Restart the game to apply."],de:["Spielsprache","Zum Speichern Einstellungen schließen. Danach das Spiel neu starten."],es:["Idioma del juego","Cierra ajustes para guardar. Reinicia el juego para aplicar."]};
         var text:Array=labels[this._translator.language] || labels.en;
         this._languageLabel.text=text[0]; this._languageHint.text=text[1];
      }

      private function initFrameRateChoice() : void
      {
         this._frameRateRow = new Sprite();
         addChild(this._frameRateRow);
         this._frameRateLabel = this.languageText(this._frameRateRow,"",0,3,145);
         this._frameRateTrack = new Sprite();
         this._frameRateTrack.x = 150;
         this._frameRateTrack.y = 14;
         this._frameRateTrack.buttonMode = true;
         this._frameRateTrack.graphics.beginFill(0xb6ae8c);
         this._frameRateTrack.graphics.drawRoundRect(0,-4,150,8,8);
         this._frameRateTrack.graphics.endFill();
         this._frameRateRow.addChild(this._frameRateTrack);
         this._frameRateThumb = new Sprite();
         this._frameRateThumb.buttonMode = true;
         this._frameRateThumb.graphics.beginFill(0x725d37);
         this._frameRateThumb.graphics.lineStyle(2,0xffffff);
         this._frameRateThumb.graphics.drawCircle(0,0,8);
         this._frameRateThumb.graphics.endFill();
         this._frameRateTrack.addChild(this._frameRateThumb);
         this._frameRateTrack.addEventListener(MouseEvent.MOUSE_DOWN,this.frameRatePointerDown);
         this._frameRateValue = this.languageText(this._frameRateRow,"",307,3,60);
         this._frameRateHint = this.languageText(this._frameRateRow,"",0,32,360);
         this._frameRateHint.wordWrap = true;
         this._frameRateHint.height = 35;
      }

      private function updateFrameRateChoice() : void
      {
         var saved:SharedObject = SharedObject.getLocal("BoufbowlPreferences","/");
         this._frameRateTarget = Number(saved.data.frameRateTarget);
         if(com.ankamagames.boufbowl.BoufbowlClient.ruffleRuntime)
            this._frameRateTarget = com.ankamagames.boufbowl.BoufbowlClient.browserFrameRate;
         if(isNaN(this._frameRateTarget) || this._frameRateTarget < 25 || this._frameRateTarget > 240)
         {
            this._frameRateTarget = Boolean(saved.data.limitFrameRate25) ? 25 : 60;
         }
         var labels:Object = {
            fr:["Limite FPS","25–240 FPS · réglage en jeu","L’écran ou le moteur peut plafonner la cadence."],
            en:["FPS limit","25–240 FPS · adjustable in game","The display or runtime may cap the actual rate."],
            de:["FPS-Limit","25–240 FPS · im Spiel einstellbar","Anzeige oder Laufzeitumgebung können die Rate begrenzen."],
            es:["Límite FPS","25–240 FPS · ajustable en el juego","La pantalla o el motor pueden limitar la frecuencia."]
         };
         var text:Array = labels[this._translator.language] || labels.en;
         this._frameRateLabel.text = text[0];
         this._frameRateValue.text = Math.round(this._frameRateTarget) + " FPS";
         this._frameRateHint.text = text[2];
         this._frameRateThumb.x = (this._frameRateTarget - 25) / 215 * 150;
         if(stage != null)
         {
            stage.frameRate = this._frameRateTarget;
         }
      }

      private function frameRatePointerDown(event:MouseEvent) : void
      {
         if(stage == null)
         {
            return;
         }
         this._frameRateDragging = true;
         stage.addEventListener(MouseEvent.MOUSE_MOVE,this.frameRatePointerMove);
         stage.addEventListener(MouseEvent.MOUSE_UP,this.frameRatePointerUp);
         this.setFrameRateFromPointer(event);
         event.stopPropagation();
      }

      private function frameRatePointerMove(event:MouseEvent) : void
      {
         if(!this._frameRateDragging)
         {
            return;
         }
         this.setFrameRateFromPointer(event);
         event.updateAfterEvent();
      }

      private function frameRatePointerUp(event:MouseEvent) : void
      {
         if(!this._frameRateDragging)
         {
            return;
         }
         this._frameRateDragging = false;
         stage.removeEventListener(MouseEvent.MOUSE_MOVE,this.frameRatePointerMove);
         stage.removeEventListener(MouseEvent.MOUSE_UP,this.frameRatePointerUp);
         var saved:SharedObject = SharedObject.getLocal("BoufbowlPreferences","/");
         saved.data.frameRateTarget = this._frameRateTarget;
         if(!com.ankamagames.boufbowl.BoufbowlClient.ruffleRuntime)
            com.ankamagames.boufbowl.BoufbowlClient.preferredFrameRate = this._frameRateTarget;
         delete saved.data.limitFrameRate25;
         saved.flush();
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.OPTIONS_CHECKBOX_CHANGED));
      }

      private function setFrameRateFromPointer(event:MouseEvent) : void
      {
         var local:Point = this._frameRateTrack.globalToLocal(new Point(event.stageX,event.stageY));
         var normalized:Number = Math.max(0,Math.min(1,local.x / 150));
         this._frameRateTarget = 25 + Math.round(normalized * 43) * 5;
         this._frameRateTarget = Math.min(240,this._frameRateTarget);
         if(com.ankamagames.boufbowl.BoufbowlClient.ruffleRuntime)
         {
            this._frameRateTarget = Math.min(60,this._frameRateTarget);
            com.ankamagames.boufbowl.BoufbowlClient.browserFrameRate = this._frameRateTarget;
         }
         this._frameRateThumb.x = (this._frameRateTarget - 25) / 215 * 150;
         this._frameRateValue.text = Math.round(this._frameRateTarget) + " FPS";
         if(stage != null)
         {
            stage.frameRate = this._frameRateTarget;
         }
      }

      public function saveLanguage() : void
      {
         if(this._languageCodes.indexOf(this._selectedLanguage)<0) return;
         var saved:SharedObject=SharedObject.getLocal("BoufbowlPreferences","/");
         saved.data.language=this._selectedLanguage; saved.flush();
      }

      private function computeVersionInfos() : String
      {
         var _loc1_:String = "v" + this._config.version + " / Player " + Capabilities.version;
         if(Capabilities.isDebugger)
         {
            _loc1_ += " (debug)";
         }
         return _loc1_;
      }
      
      private function checkboxClickHandler(param1:MouseEvent) : void
      {
         dispatchEvent(new InterfaceSoundEvent(InterfaceSoundEvents.LOGIN_CHECKBOX_CLICKED));
      }
      
      private function layoutOptions() : void
      {
         var _loc2_:Boolean = false;
         var _loc3_:String = null;
         var _loc4_:DisplayObject = null;
         var _loc1_:IMapIterator = this._config.optionsVisibility.getMapIterator();
         var _loc5_:int = optionsYReference.y;
         while(_loc1_.hasNext())
         {
            _loc2_ = Boolean(_loc1_.getNext());
            _loc3_ = _loc1_.getKey() + this.CONTAINER_SUFFIX;
            _loc4_ = getChildByName(_loc3_);
            if(_loc4_ == null)
            {
               throw new Error("There is no container with the name " + _loc3_ + ".");
            }
            _loc4_.visible = _loc2_;
            if(_loc2_)
            {
               _loc4_.y = _loc5_;
               _loc5_ += _loc4_.height;
               if(_loc4_ == soundContainer)
               {
                  this._volumeRow.x = soundContainer.x;
                  this._volumeRow.y = _loc5_;
                  _loc5_ += 75;
               }
            }
         }
         this._volumeRow.visible = soundContainer.visible;
         this._languageRow.x=soundContainer.x;
         this._languageRow.y=_loc5_+5;
         _loc5_+=75;
         this._frameRateRow.x=soundContainer.x;
         this._frameRateRow.y=_loc5_+5;
         _loc5_+=65;
         buttonsContainer.y = _loc5_;
         _loc5_ += buttonsContainer.height;
         optionsMainBackground.height = _loc5_ - optionsMainBackground.y;
      }
   }
}

