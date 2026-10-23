"""Isolate the current Flash/Wine frame scheduler from game and renderer costs."""
import math
from tools.client_probe import compile_probe, ROOT_CLASS
from tools.game_config import ROOT


def runtime_probe_source(target):
    if not math.isfinite(target) or not 25 <= target <= 1000:
        raise ValueError('FPS probe target must be between 25 and 1000')
    return r'''package com.ankamagames.boufbowl {
      import flash.display.Sprite;
      import flash.events.Event;
      import flash.external.ExternalInterface;
      import flash.system.Capabilities;
      import flash.text.TextField;
      import flash.text.TextFormat;
      import flash.utils.getTimer;
      public class BoufbowlClient extends Sprite {
         private var label:TextField=new TextField();
         private var frames:int=0;
         private var windowStart:int;
         private var totalFrames:int=0;
         private var started:int;
         public function BoufbowlClient() {
            if(stage!=null) initialize();
            else addEventListener(Event.ADDED_TO_STAGE,initialize);
         }
         private function initialize(event:Event=null):void {
            removeEventListener(Event.ADDED_TO_STAGE,initialize);
            stage.frameRate=__TARGET__;
            label.defaultTextFormat=new TextFormat('_sans',24,0xffffff);
            label.background=true;label.backgroundColor=0x17231f;
            label.width=900;label.height=160;label.selectable=false;
            label.text='Blank runtime probe: waiting for first sample';addChild(label);
            windowStart=started=getTimer();
            addEventListener(Event.ENTER_FRAME,tick);
            if(ExternalInterface.available) ExternalInterface.addCallback('fpsProbeStats',stats);
         }
         private function stats():Object {
            return {requested:__TARGET__,stage:stage.frameRate,frames:totalFrames,
               elapsedMs:getTimer()-started,runtime:Capabilities.version,text:label.text};
         }
         private function tick(event:Event):void {
            frames++;totalFrames++;
            var now:int=getTimer();var elapsed:int=now-windowStart;
            if(elapsed<500)return;
            label.text='Runtime FPS: '+Math.round(frames*1000/elapsed)+' / '+stage.frameRate+
               '\n'+Capabilities.version+'\nBlank probe: no game, animation or 3D scene';
            frames=0;windowStart=now;
         }
      }
   }'''.replace('__TARGET__',str(float(target)))


def build_runtime_probe(target, root=ROOT):
    source=runtime_probe_source(target)
    base=root/'bin/boufbowl-client-1.9.6.swf'
    if not base.is_file():
        base=root/'bin/base/boufbowl-client-1.9.6.swf'
    return compile_probe(base,[(ROOT_CLASS,source)],root)
