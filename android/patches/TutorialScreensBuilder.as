package com.ankamagames.boufbowl.client.tutorial
{
   import as3.collections.ILinkedList;
   import as3.collections.LinkedList;
   import com.ankamagames.boufbowl.audio.AudioConfiguration;
   import com.ankamagames.boufbowl.audio.ScriptSounds;
   import com.ankamagames.boufbowl.client.i18n.LangConstants;
   import com.ankamagames.boufbowl.client.tutorial.characters.TutorialFieldEntitiesRepository;
   import com.ankamagames.boufbowl.client.tutorial.characters.TutorialSpeechCharacters;
   import com.ankamagames.boufbowl.client.tutorial.screen.TutorialAdvanceType;
   import com.ankamagames.boufbowl.client.tutorial.screen.builder.TutorialScreenBuilderFactory;
   import com.ankamagames.boufbowl.client.tutorial.screen.builder.TutorialScriptScreenBuilder;
   import com.ankamagames.boufbowl.client.tutorial.screen.builder.TutorialSpeechScreenBuilder;
   import com.ankamagames.boufbowl.client.tutorial.screen.builder.TutorialStrategicScreenBuilder;
   import com.ankamagames.boufbowl.client.tutorial.screen.builder.TutorialVideoScreenBuilder;
   import com.ankamagames.boufbowl.client.tutorial.script.ClassSpellScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step0TutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step1TutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step1bisTutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step2TutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step3TutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step4TutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step5TutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.script.Step6tutorialScript;
   import com.ankamagames.boufbowl.client.tutorial.strategic.StrategicBoufballConfig;
   import com.ankamagames.boufbowl.client.tutorial.strategic.StrategicBoufbowlerConfig;
   import com.ankamagames.boufbowl.protocol.BoufballStatus;
   import com.ankamagames.boufbowl.protocol.RegularOrderData.Element;
   import com.ankamagames.xgaming.audio.controller.data.LoopsData;
   import com.ankamagames.xgaming.utils.i18n.ITranslator;
   import com.netease.protobuf.Int64;
   
   public class TutorialScreensBuilder
   {
      
      private var _screenBuilderFactory:TutorialScreenBuilderFactory;
      
      private var _translator:ITranslator;
      
      private var _characters:TutorialFieldEntitiesRepository;
      
      private var _list:ILinkedList;
      
      private const FAKE_ORDERS_STEP_01:String = "Step01";
      
      private const FAKE_ORDERS_STEP_02:String = "Step02";
      
      private const FAKE_ORDERS_STEP_03:String = "Step03";
      
      private const FAKE_ORDERS_STEP_04:String = "Step04";
      
      private const FAKE_ORDERS_STEP_05:String = "Step05";
      
      private const FAKE_ORDERS_STEP_06:String = "Step06";
      
      private const SHOW_TOUCHDOWN_LINES:String = "Step00";
      
      private const CLASS_ORDER_BUTTON:String = "Step07Class";
      
      private const CLASS_ORDER_PANEL:String = "Step08Class";
      
      public function TutorialScreensBuilder(param1:TutorialScreenBuilderFactory, param2:ITranslator)
      {
         super();
         this._translator = param2;
         this._screenBuilderFactory = param1;
      }
      
      public function build(param1:TutorialFieldEntitiesRepository) : ILinkedList
      {
         this._characters = param1;
         this._list = new LinkedList();
         this.addVideoScreen().videoFile("app:/assets/videos/tutorial-intro.mp4").speech(TutorialSpeechCharacters.MEDONEC,"<br />" + this._translator.getText(LangConstants.TUTORIAL_INTRO_0),true,false).advanceType(TutorialAdvanceType.FORCABLE);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,"",true,false).advanceType(TutorialAdvanceType.AUTOMATIC).playSound(AudioConfiguration.MUSIC,"music/tuto_loop_01.mp3",LoopsData.MAX_LOOPS);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_INTRO_1),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_01.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,"",true,false).advanceType(TutorialAdvanceType.AUTOMATIC).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_08.mp3",LoopsData.NO_LOOP);
         this.addVideoScreen().videoFile("app:/assets/videos/layout_tuto_02.mp4").loop().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_INTRO_2) + "<br /><br />" + this._translator.getText(LangConstants.TUTORIAL_INTRO_3)).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.AMBIANT,ScriptSounds.AMB_HILL,LoopsData.MAX_LOOPS);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.BOUFBOUZEUX_2,this._translator.getText(LangConstants.TUTORIAL_INTRO_5),false,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_iop_01.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC_2,this._translator.getText(LangConstants.TUTORIAL_INTRO_6),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_02.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.BOUFBOUZEUX_3,this._translator.getText(LangConstants.TUTORIAL_INTRO_7),false,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_iop_02.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_INTRO_8),true,false).advanceType(TutorialAdvanceType.USER);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_INTRO_9),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_04.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.ENUTROFETTE_2,this._translator.getText(LangConstants.TUTORIAL_INTRO_10),false,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_enu_01.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC_2,this._translator.getText(LangConstants.TUTORIAL_INTRO_11),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_05.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,"",true,false).advanceType(TutorialAdvanceType.AUTOMATIC).playSound(AudioConfiguration.FX,"tuto/layout_tuto_01.mp3",LoopsData.NO_LOOP);
         this.addVideoScreen().videoFile("app:/assets/videos/layout_tuto_01.mp4").speech(TutorialSpeechCharacters.MEDONEC_2,this._translator.getText(LangConstants.TUTORIAL_INTRO_12),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_09.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.DISABLE_DIRECTION_ARROWS).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_0_1),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(5,-10)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(-6,-3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BYSTANDER_1).position(-10,7)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BYSTANDER_2).position(-8,10)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BYSTANDER_3).position(-7,-7)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.ON_GROUND).position(0,3)).overlayMovieClip(this.SHOW_TOUCHDOWN_LINES).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_10.mp3"
         ,LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_0_2),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_06.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_0_3),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_07.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new Step0TutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_0_1),true,false).advanceType(TutorialAdvanceType.AUTOMATIC).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_11.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_1_1),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_01.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.NONE).isCheckPoint().overlayMovieClip(this.FAKE_ORDERS_STEP_01).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_1_2),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(-1,-4)).blinkingCell(-1,3).boufballConfig(this.getBoufballConfig().status(BoufballStatus.ON_GROUND).position(0,3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_02.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.ALL).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_1_3),true,true).blinkingCell(-1,3).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(-1,-4)).boufbowlerValidationConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).targetCell(-1,3).position(-1,-4)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.ON_GROUND).position(0,3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_03.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new Step1TutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_1_1),true,false).advanceType(TutorialAdvanceType.AUTOMATIC);
         this.addScriptScreen().script(new Step1bisTutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_1_2),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_04.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.NONE).isCheckPoint().overlayMovieClip(this.FAKE_ORDERS_STEP_02).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_2_1),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(-1,3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(3,3)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.BOUFTOU)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_05.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.ALL).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_2_2),true,true).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(-1,3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(3,3)).boufbowlerValidationConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).targetBoufbowler(TutorialFieldEntitiesRepository.BOUFTOU).position(-1,3)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.BOUFTOU)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_06.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new Step2TutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_2_1),true,false).advanceType(TutorialAdvanceType.AUTOMATIC);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_2_2),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_07.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.NONE).isCheckPoint().overlayMovieClip(this.FAKE_ORDERS_STEP_03).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_3_1),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(3,-3).targetBoufbowler(TutorialFieldEntitiesRepository.BOUFTOU).orderElement(Element.EARTH,3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(3,-5)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.BOUFTOU)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_08.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.DISABLE_DIRECTION_ARROWS).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_3_2),true,true).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(3,-3).targetBoufbowler(TutorialFieldEntitiesRepository.BOUFTOU)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(3,-5)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.BOUFTOU)).boufbowlerValidationConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(3,-3).orderElement(Element.EARTH,1)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_09.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new Step3TutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_3_1),true,false).advanceType(TutorialAdvanceType.AUTOMATIC);
         this.addStrategicScreen(UserInteractionMode.NONE).isCheckPoint().overlayMovieClip(this.FAKE_ORDERS_STEP_04).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_4_1),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(3,-3).targetCell(8,-8).orderElement(Element.AIR,3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(5,-2).ko()).boufballConfig(this.getBoufballConfig().status(BoufballStatus.ON_GROUND).position(6,-7)).blinkingCell(8,-8).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_10.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.DISABLE_DIRECTION_ARROWS).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_4_2),true,true).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(3,-3).targetCell(8,-8)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(5,-2).ko()).boufbowlerValidationConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).targetCell(8,-8).orderElementChoice([Element.AIR,Element.FIRE]).position(3,-3)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.ON_GROUND).position(6,-7)).blinkingCell(8,-8).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_11.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new Step4TutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_4_1),true,false).advanceType(TutorialAdvanceType.AUTOMATIC);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.ENUTROFETTE,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_4_2),false,false).playSound(AudioConfiguration.FX,"tuto/tuto_enu_03.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_4_3),true,false).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_08.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.NONE).isCheckPoint().overlayMovieClip(this.FAKE_ORDERS_STEP_05).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_5_1),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(8,-8).targetCell(13,-8).orderElement(Element.AIR,3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(5,-3).targetCell(8,-3).orderElement(Element.AIR,2)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(5,-2).ko()).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_01.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.DISABLE_DIRECTION_ARROWS).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_5_2),true,true).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(8,-8).targetCell(13,-8)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(5,-3).targetCell(8,-3)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(5,-2).ko()).boufbowlerValidationConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).orderElement(Element.AIR,1).position(8,-8).passTarget(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER)).boufbowlerValidationConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).orderElement(Element.AIR,1).position(5,-3)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER))
         .boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_02.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new Step5TutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_5_1),true,false).advanceType(TutorialAdvanceType.AUTOMATIC);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_5_2),true,false).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_03.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.NONE).isCheckPoint().overlayMovieClip(this.FAKE_ORDERS_STEP_06).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_6_1),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(13,-8).ko()).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(8,-3).ko()).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(12,-7)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.ON_GROUND).position(16,-7)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_04.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.ALL).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_STRATEGIC_STEP_6_2),true,true).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(13,-8).ko()).blinkingCell(20,-8).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(8,-3).ko()).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(12,-7)).boufbowlerValidationConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).orderElement(Element.WATER,1).orderElement(Element.FIRE,1).position(13,-8).targetCell(20,-8)).boufballConfig(this.getBoufballConfig().status(BoufballStatus.ON_GROUND).position(16,-7)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_05.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new Step6tutorialScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_RESOLUTION_STEP_6_1),true,false).advanceType(TutorialAdvanceType.AUTOMATIC);
         this.addStrategicScreen(UserInteractionMode.ALL).isCheckPoint().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_CLASSORDER_1),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(20,-8)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(8,-3).ko()).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(12,-7).ko()).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER)).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_10.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.ALL).isCheckPoint().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_CLASSORDER_2),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(20,-8)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(8,-3).ko()).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(12,-7).ko()).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER)).overlayMovieClip(this.CLASS_ORDER_BUTTON).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_07.mp3",LoopsData.NO_LOOP);
         this.addScriptScreen().script(new ClassSpellScript()).speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_CLASSORDER_3),true,false).advanceType(TutorialAdvanceType.USER).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_11.mp3",LoopsData.NO_LOOP);
         this.addStrategicScreen(UserInteractionMode.ALL).isCheckPoint().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_CLASSORDER_4),true,false).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER).position(20,-8)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.SECOND_BOUFBOWLER).position(8,-3).ko()).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.MEDONEC).position(-3,6)).boufbowlerConfig(this.getBoufbowlerConfig(TutorialFieldEntitiesRepository.BOUFTOU).position(12,-7).ko()).boufballConfig(this.getBoufballConfig().status(BoufballStatus.HELD,TutorialFieldEntitiesRepository.FIRST_BOUFBOWLER)).overlayMovieClip(this.CLASS_ORDER_PANEL).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_08.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,"",true,false).advanceType(TutorialAdvanceType.AUTOMATIC).playSound(AudioConfiguration.FX,"tuto/layout_tuto_02.mp3",LoopsData.NO_LOOP);
         this.addVideoScreen().videoFile("app:/assets/videos/layout_tuto_03.mp4").speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_OUTRO_1),true,false).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_08.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_OUTRO_2),true,false).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_07.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_OUTRO_3),true,false).playSound(AudioConfiguration.FX,"tuto/tuto_cowboy_10.mp3",LoopsData.NO_LOOP);
         this.addSpeechOnlyScreen().speech(TutorialSpeechCharacters.MEDONEC,"",true,false).advanceType(TutorialAdvanceType.AUTOMATIC).stopSounds(AudioConfiguration.AMBIANT);
         this.addVideoScreen().videoFile("app:/assets/videos/tutorial-outro.mp4").speech(TutorialSpeechCharacters.MEDONEC,this._translator.getText(LangConstants.TUTORIAL_OUTRO_4),true,false).advanceType(TutorialAdvanceType.FORCABLE).stopSounds(AudioConfiguration.MUSIC);
         return this._list;
      }
      
      private function addScriptScreen() : TutorialScriptScreenBuilder
      {
         var _loc1_:TutorialScriptScreenBuilder = this._screenBuilderFactory.createScriptScreenBuilder();
         this._list.addItem(_loc1_);
         return _loc1_;
      }
      
      private function addStrategicScreen(param1:uint) : TutorialStrategicScreenBuilder
      {
         var _loc2_:TutorialStrategicScreenBuilder = this._screenBuilderFactory.createStrategicScreenBuilder(param1,this._characters);
         this._list.addItem(_loc2_);
         return _loc2_;
      }
      
      private function addSpeechOnlyScreen() : TutorialSpeechScreenBuilder
      {
         var _loc1_:TutorialSpeechScreenBuilder = this._screenBuilderFactory.createSpeechOnlyScreenBuilder();
         this._list.addItem(_loc1_);
         return _loc1_;
      }
      
      private function addVideoScreen() : TutorialVideoScreenBuilder
      {
         var _loc1_:TutorialVideoScreenBuilder = this._screenBuilderFactory.createVideoScreenBuilder();
         this._list.addItem(_loc1_);
         return _loc1_;
      }
      
      private function getBoufbowlerConfig(param1:Int64) : StrategicBoufbowlerConfig
      {
         return new StrategicBoufbowlerConfig(param1,this._characters,this._translator);
      }
      
      private function getBoufballConfig() : StrategicBoufballConfig
      {
         return new StrategicBoufballConfig();
      }
   }
}

