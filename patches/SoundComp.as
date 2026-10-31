package com.ankamagames.xgaming.audio.base
{
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.xgaming.audio.controller.data.PanData;
   import com.ankamagames.xgaming.audio.controller.data.VolumeData;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.reider.log4AS3.ILogger;
   import flash.events.Event;
   import flash.events.EventDispatcher;
   import flash.events.IOErrorEvent;
   import flash.media.Sound;
   import flash.media.SoundChannel;
   import flash.media.SoundLoaderContext;
   import flash.media.SoundTransform;
   import flash.net.URLRequest;

   public class SoundComp extends EventDispatcher implements ISoundComp
   {

      protected var _isLoading:Boolean = false;

      private var _lastRequestedURL:String;
      private var _requestedLoops:int = 0;
      private var _playRequested:Boolean = false;

      public static function fallbackMusicURL(url:String) : String
      {
         if(url == null) return null;
         var match:Array = /^((?:.*\/)?music\/)([^\/?#]+)\.mp3([?#].*)?$/.exec(url);
         if(match == null || /^music_(tactic|resolution)_loop_/.test(match[2])) return null;
         var phase:String = /tactique|tactic/.test(match[2]) ? "tactic" : (/resolution/.test(match[2]) ? "resolution" : null);
         if(phase == null) return null;
         var suffix:Array = /_(\d+)$/.exec(match[2]);
         var index:int = suffix == null ? 1 : (int(suffix[1]) - 1) % 4 + 1;
         return match[1] + "music_" + phase + "_loop_0" + index + ".mp3" + (match[3] || "");
      }

      private var _sound:Sound;

      private var _soundChannel:SoundChannel;

      private var _soundTransform:SoundTransform;

      private var _isPlaying:Boolean = false;

      private const LOGGER:ILogger = LoggerFactory.getLogger(SoundComp);

      public function SoundComp(param1:URLRequest = null, param2:SoundLoaderContext = null)
      {
         super();
         this.init(param1,param2);
      }

      final public function get isPlaying() : Boolean
      {
         return this._isPlaying;
      }

      public function get volume() : VolumeData
      {
         var _loc1_:Number = this._soundTransform.volume;
         if(_loc1_ < VolumeData.SILENCE.value)
         {
            _loc1_ = VolumeData.SILENCE.value;
         }
         return new VolumeData(_loc1_);
      }

      public function set volume(param1:VolumeData) : void
      {
         if(!param1)
         {
            throw new ArgumentError("volume can\'t be null");
         }
         this._soundTransform.volume = param1.value;
         this.applySoundTransformToSoundChannel();
      }

      public function get pan() : PanData
      {
         var _loc1_:Number = this._soundTransform.pan;
         if(_loc1_ < PanData.LEFT.value)
         {
            _loc1_ = PanData.LEFT.value;
         }
         else if(_loc1_ > PanData.RIGHT.value)
         {
            _loc1_ = PanData.RIGHT.value;
         }
         return new PanData(_loc1_);
      }

      public function set pan(param1:PanData) : void
      {
         if(!param1)
         {
            throw new ArgumentError("pan can\'t be null");
         }
         this._soundTransform.pan = param1.value;
         this.applySoundTransformToSoundChannel();
      }

      final public function get position() : Number
      {
         return this._soundChannel ? this._soundChannel.position : 0;
      }

      final public function get length() : Number
      {
         var _loc1_:Number = NaN;
         if(this._isLoading)
         {
            _loc1_ = this._sound.length * this._sound.bytesTotal / this._sound.bytesLoaded;
            return isNaN(_loc1_) ? 0 : _loc1_;
         }
         return this._sound.length;
      }

      final public function load(param1:URLRequest) : void
      {
         this._playRequested = false;
         this.createSound(param1);
      }

      final public function play(param1:int = 0) : String
      {
         var state:String = null;
         var soundC:SoundChannel = null;
         var loops:int = param1;
         this._requestedLoops = param1;
         this._playRequested = true;
         try
         {
            soundC = this._sound.play(0,loops);
            if(soundC == null)
            {
               this._isPlaying = false;
               state = SoundPlayResult.NO_FREE_CHANNEL;
            }
            else
            {
               this._isPlaying = true;
               this.setSoundChannel(soundC);
               state = SoundPlayResult.SUCCESS;
            }
         }
         catch(err:ArgumentError)
         {
            _isPlaying = false;
            state = SoundPlayResult.NO_SOUND_TO_PLAY;
         }
         return state;
      }

      final public function stop() : void
      {
         this._playRequested = false;
         this._isPlaying = false;
         if(this._soundChannel)
         {
            this._soundChannel.stop();
         }
      }

      final public function close() : void
      {
         this._playRequested = false;
         if(this._isLoading)
         {
            try
            {
               this._isLoading = false;
               this._sound.close();
            }
            catch(error:Error)
            {
               LOGGER.error("_isLoading property seems to be bad managed.");
            }
         }
      }

      public function setSound(param1:Sound, param2:Object = null) : void
      {
         this._playRequested = false;
         this._isPlaying = false;
         this._isLoading = param2 === null ? this.isCurrentlyLoading(param1) : Boolean(param2);
         this.setSoundInstance(param1);
      }

      private function isCurrentlyLoading(param1:Sound) : Boolean
      {
         return param1.isBuffering || param1.bytesTotal > 0 && param1.bytesLoaded < param1.bytesTotal;
      }

      private function init(param1:URLRequest = null, param2:SoundLoaderContext = null) : void
      {
         this._soundTransform = new SoundTransform();
         this.createSound(param1,param2);
      }

      private function createSound(param1:URLRequest, param2:SoundLoaderContext = null) : void
      {
         if(this._sound)
         {
            this.destroySound();
         }
         this._isPlaying = false;
         this.setSoundInstance(new Sound(),param1,param2);
      }

      private function setSoundInstance(param1:Sound, param2:URLRequest = null, param3:SoundLoaderContext = null) : void
      {
         this._lastRequestedURL = param2 != null ? param2.url : null;
         this._sound = param1;
         this._sound.addEventListener(Event.COMPLETE,this.eventsHandler);
         this._sound.addEventListener(IOErrorEvent.IO_ERROR,this.eventsHandler);
         if(param2 != null)
         {
            this._sound.load(param2,param3);
            this._isLoading = true;
         }
      }

      private function applySoundTransformToSoundChannel() : void
      {
         if(this._soundChannel != null)
         {
            this._soundChannel.soundTransform = this._soundTransform;
         }
      }

      private function destroySound() : void
      {
         this.close();
         if(this._soundChannel)
         {
            this.destroySoundChannel();
         }
         this._sound.removeEventListener(Event.COMPLETE,this.eventsHandler);
         this._sound.removeEventListener(IOErrorEvent.IO_ERROR,this.eventsHandler);
         this._sound = null;
      }

      private function setSoundChannel(param1:SoundChannel) : void
      {
         if(this._soundChannel)
         {
            this.destroySoundChannel();
         }
         this._soundChannel = param1;
         this.applySoundTransformToSoundChannel();
         this._soundChannel.addEventListener(Event.SOUND_COMPLETE,this.eventsHandler);
      }

      private function destroySoundChannel() : void
      {
         this._soundChannel.stop();
         this._soundChannel.removeEventListener(Event.SOUND_COMPLETE,this.eventsHandler);
         this._soundChannel = null;
      }

      private function eventsHandler(param1:Event) : void
      {
         switch(param1.type)
         {
            case IOErrorEvent.IO_ERROR:
               var fallback:String = fallbackMusicURL(this._lastRequestedURL != null ? this._lastRequestedURL : this._sound.url);
               if(fallback != null)
               {
                  var resume:Boolean = this._playRequested;
                  var loops:int = this._requestedLoops;
                  this._isLoading = false;
                  this.createSound(new URLRequest(fallback));
                  if(resume) this.play(loops);
                  return;
               }
               this._isPlaying = false;
               this._isLoading = false;
               break;
            case Event.COMPLETE:
               this._isLoading = false;
               break;
            case Event.SOUND_COMPLETE:
               this._isPlaying = false;
               break;
            default:
               throw new IllegalStateError("event type not handled");
         }
         if(param1.type == IOErrorEvent.IO_ERROR)
         {
            this.LOGGER.error("Sound URL not found : " + (this._lastRequestedURL != null ? this._lastRequestedURL : "") + " " + (param1 as IOErrorEvent).text);
         }
         else
         {
            dispatchEvent(param1);
         }
      }
   }
}
