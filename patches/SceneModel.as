package com.ankamagames.boufbowl.resolution.display.model
{
   import as3.collections.ArrayList;
   import as3.collections.IList;
   import as3.collections.IMap;
   import as3.collections.LinkedList;
   import as3.collections.Map;
   import as3.collections.iterators.IIterator;
   import com.adobe.errors.IllegalStateError;
   import com.ankamagames.boufbowl.resolution.display.animation.IBoufbowlerSprite;
   import com.ankamagames.boufbowl.resolution.display.model.event.BoufbowlerChangeEvent;
   import com.ankamagames.boufbowl.resolution.display.model.event.ColorMatrixFilterEvent;
   import com.ankamagames.boufbowl.resolution.display.model.event.OnomatopeiaChangeEvent;
   import com.ankamagames.boufbowl.resolution.display.model.event.VisibilityChangedEvent;
   import com.netease.protobuf.Int64;
   import flash.events.EventDispatcher;
   import flash.filters.ColorMatrixFilter;

   public class SceneModel extends EventDispatcher implements IUpdatable
   {

      private var _visible:Boolean;

      private var _mobileFactory:IMobileFactory;

      private var _boufbowlers:IMap;

      private var _boufbowlerLookup:Object;

      private var _coloredBoufbowler:IList;

      private var _ball:IBall;

      private var _camera:BoufbowlCameraController;

      private var _grid:IGrid;

      private var _onomatopeias:IList;

      public function SceneModel(param1:IMobileFactory, param2:BoufbowlCameraController)
      {
         super();
         this._mobileFactory = param1;
         this._camera = param2;
         this.init();
      }

      public function set visible(param1:Boolean) : void
      {
         if(this._visible == param1)
         {
            return;
         }
         this._visible = param1;
         dispatchEvent(new VisibilityChangedEvent(this._visible));
      }

      public function get ball() : IBall
      {
         return this._ball;
      }

      public function get grid() : IGrid
      {
         return this._grid;
      }

      public function get camera() : BoufbowlCameraController
      {
         return this._camera;
      }

      public function boufbowlers() : IList
      {
         var _loc1_:IList = new ArrayList();
         var _loc2_:IIterator = this._boufbowlers.getKeyIterator();
         while(_loc2_.hasNext())
         {
            _loc1_.addItem(_loc2_.getNext());
         }
         return _loc1_;
      }

      public function addBoufbowler(id:Int64, sprite:IBoufbowlerSprite, team:BoufbowlTeam) : IBoufbowler
      {
         var boufbowler:IBoufbowler = this.createBoufbowler(sprite,team);
         this._boufbowlers.addItem(id,boufbowler);
         delete this._boufbowlerLookup[this.boufbowlerKey(id)];
         dispatchEvent(BoufbowlerChangeEvent.boufbowlerAdded(boufbowler));
         return boufbowler;
      }

      public function removeBoufbowler(id:Int64) : IBoufbowler
      {
         delete this._boufbowlerLookup[this.boufbowlerKey(id)];
         var storedId:Int64 = null;
         var boufbowler:IBoufbowler = this._boufbowlers.getItem(id);
         if(boufbowler != null)
         {
            this._boufbowlers.removeKey(id);
            boufbowler.removeAllFxs();
            dispatchEvent(BoufbowlerChangeEvent.boufbowlerRemoved(boufbowler));
            return boufbowler;
         }
         var keys:IIterator = this._boufbowlers.getKeyIterator();
         while(keys.hasNext())
         {
            storedId = keys.getNext();
            if(storedId.equals(id))
            {
               boufbowler = this._boufbowlers.getItem(storedId);
               this._boufbowlers.removeKey(storedId);
               boufbowler.removeAllFxs();
               dispatchEvent(BoufbowlerChangeEvent.boufbowlerRemoved(boufbowler));
               return boufbowler;
            }
         }
         return null;
      }

      public function getBoufbowler(id:Int64) : IBoufbowler
      {
         var storedId:Int64 = null;
         var boufbowler:IBoufbowler = this._boufbowlers.getItem(id);
         if(boufbowler != null)
         {
            return boufbowler;
         }
         var lookupKey:String = this.boufbowlerKey(id);
         var cached:Int64 = this._boufbowlerLookup[lookupKey];
         if(cached != null && cached.equals(id))
         {
            boufbowler = this._boufbowlers.getItem(cached);
            if(boufbowler != null) return boufbowler;
         }
         var keys:IIterator = this._boufbowlers.getKeyIterator();
         while(keys.hasNext())
         {
            storedId = keys.getNext();
            if(storedId.equals(id))
            {
               this._boufbowlerLookup[lookupKey] = storedId;
               return this._boufbowlers.getItem(storedId);
            }
         }
         throw new IllegalStateError("Retrieving unknown boufbowler " + id);
      }

      public function addOnomatopeia(param1:Number, param2:Number, param3:String, param4:int, param5:Function) : Onomatopeia
      {
         var _loc6_:Onomatopeia = this.createOnomatopeia(param1,param2,param3,param4,param5);
         this._onomatopeias.addItem(_loc6_);
         dispatchEvent(OnomatopeiaChangeEvent.onomatopeiaAdded(_loc6_));
         return _loc6_;
      }

      public function removeOnomatopeia(param1:Onomatopeia) : Onomatopeia
      {
         this._onomatopeias.removeItem(param1);
         dispatchEvent(OnomatopeiaChangeEvent.onomatopeiaRemoved(param1));
         return param1;
      }

      public function addColorFX(param1:IBoufbowler) : void
      {
         var _loc4_:IBoufbowler = null;
         this._coloredBoufbowler.addItem(param1);
         param1.colorFilter = null;
         var _loc2_:ColorMatrixFilter = this.createGreyFilter();
         var _loc3_:IIterator = this._boufbowlers.getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext() as IBoufbowler;
            if(_loc4_ != param1 && !this._coloredBoufbowler.hasItem(_loc4_) && _loc4_.colorFilter == null)
            {
               _loc4_.colorFilter = _loc2_;
            }
         }
         this.ball.colorFilter = _loc2_;
         dispatchEvent(ColorMatrixFilterEvent.colorAdded(_loc2_));
      }

      public function removeColorFX() : void
      {
         var _loc2_:IBoufbowler = null;
         var _loc1_:IIterator = this._boufbowlers.getIterator();
         while(_loc1_.hasNext())
         {
            _loc2_ = _loc1_.getNext() as IBoufbowler;
            _loc2_.colorFilter = null;
         }
         this._coloredBoufbowler.clear();
         this.ball.colorFilter = null;
         dispatchEvent(ColorMatrixFilterEvent.colorRemoved());
      }

      public function removeAllBoufbowlerFxs() : void
      {
         var _loc2_:IBoufbowler = null;
         var _loc1_:IIterator = this._boufbowlers.getIterator();
         while(_loc1_.hasNext())
         {
            _loc2_ = _loc1_.getNext();
            _loc2_.removeAllFxs();
         }
      }

      public function update(param1:int, param2:int) : void
      {
         this.updateBoufbowlers(param1,param2);
         this._ball.update(param1);
         this._camera.update(param2);
         this.updateOnomatopeias(param1,param2);
      }

      public function reset() : void
      {
         var _loc1_:IIterator = this._boufbowlers.getKeyIterator();
         while(_loc1_.hasNext())
         {
            this.removeBoufbowler(Int64(_loc1_.getNext()));
         }
         this.removeOnomatopeias();
         this._boufbowlerLookup = {};
         this.ball.reset();
         this.camera.reset();
         dispatchEvent(ColorMatrixFilterEvent.colorRemoved());
      }

      private function init() : void
      {
         this._visible = true;
         this._boufbowlers = new Map();
         this._boufbowlerLookup = {};
         this._coloredBoufbowler = new LinkedList();
         this._onomatopeias = new LinkedList();
         this._ball = this._mobileFactory.createBall();
         this._grid = this._mobileFactory.createGrid();
      }

      private function updateBoufbowlers(param1:int, param2:int) : void
      {
         var _loc4_:IBoufbowler = null;
         var _loc3_:IIterator = this._boufbowlers.getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext() as IBoufbowler;
            _loc4_.update(param1,param2);
         }
      }

      private function updateOnomatopeias(param1:int, param2:int) : void
      {
         var _loc4_:Onomatopeia = null;
         var _loc3_:IIterator = this._onomatopeias.getIterator();
         while(_loc3_.hasNext())
         {
            _loc4_ = _loc3_.getNext() as Onomatopeia;
            _loc4_.update(param1,param2);
         }
      }

      private function removeOnomatopeias() : void
      {
         var _loc2_:Onomatopeia = null;
         var _loc1_:IIterator = this._onomatopeias.getIterator();
         while(_loc1_.hasNext())
         {
            _loc2_ = _loc1_.getNext() as Onomatopeia;
            dispatchEvent(OnomatopeiaChangeEvent.onomatopeiaRemoved(_loc2_));
         }
         this._onomatopeias.clear();
      }

      private function boufbowlerKey(id:Int64) : String
      {
         // Keep both 32-bit words. Int64.toString() concatenates them without
         // a separator, and conversion to Number loses precision for large ids.
         return id == null ? "null" : id.high + ":" + id.low;
      }

      private function createBoufbowler(param1:IBoufbowlerSprite, param2:BoufbowlTeam) : IBoufbowler
      {
         return this._mobileFactory.createBoufbowler(param1,param2);
      }

      private function createOnomatopeia(param1:Number, param2:Number, param3:String, param4:int, param5:Function) : Onomatopeia
      {
         return this._mobileFactory.createOnomatopeia(param1,param2,param3,param4,param5);
      }

      private function createGreyFilter() : ColorMatrixFilter
      {
         var _loc1_:Array = new Array();
         _loc1_.push(0.3086,0.6094,0.082,0,0);
         _loc1_.push(0.3086,0.6094,0.082,0,0);
         _loc1_.push(0.3086,0.6094,0.082,0,0);
         _loc1_.push(0,0,0,1,0);
         return new ColorMatrixFilter(_loc1_);
      }
   }
}
