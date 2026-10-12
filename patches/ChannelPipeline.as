package com.ankamagames.xgaming.net.channel.pipeline
{
   import com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand;
   import as3.collections.ILinkedList;
   import as3.collections.LinkedList;
   import as3.collections.iterators.IIterator;
   import as3.collections.iterators.IListPointer;
   import com.ankamagames.xgaming.net.channel.ChannelHandlerContext;
   import com.ankamagames.xgaming.net.channel.IChannelDownstreamHandler;
   import com.ankamagames.xgaming.net.channel.IChannelHandler;
   import com.ankamagames.xgaming.net.channel.IChannelUpstreamHandler;
   import com.ankamagames.xgaming.net.events.ChannelDownstreamDataEvent;
   import com.ankamagames.xgaming.net.events.ChannelEvent;
   import com.ankamagames.xgaming.net.events.ChannelUpstreamDataEvent;
   import com.ankamagames.xgaming.net.events.CloseChannelRequestEvent;
   import com.ankamagames.xgaming.net.events.OpenChannelRequestEvent;
   import com.ankamagames.xgaming.utils.errors.IllegalArgumentError;
   
   public class ChannelPipeline
   {
      
      private var _contexts:ILinkedList;
      
      private var _sink:ConnectionSink;
      
      private var _host:String;
      
      private var _port:int;
      
      public function ChannelPipeline()
      {
         super();
         this._contexts = new LinkedList();
      }
      
      public function set sink(param1:ConnectionSink) : void
      {
         this._sink = param1;
      }
      
      public function addLast(param1:IChannelHandler) : void
      {
         this._contexts.addItemAtEnd(this.createContext(param1));
      }
      
      public function remove(param1:IChannelHandler) : void
      {
         this.destroyContext(param1);
      }
      
      public function sendDataUpstream(param1:Object, param2:IChannelUpstreamHandler = null) : void
      {
         if(param2 == null)
         {
            this.sendUpstream(new ChannelUpstreamDataEvent(param1));
            return;
         }
         var _loc3_:IListPointer = this.getChannelHandlerContextPointer(param2);
         if(_loc3_ == null)
         {
            return;
         }
         this.sendUpstream(new ChannelUpstreamDataEvent(param1),_loc3_);
      }
      
      public function sendDownstream(param1:Object) : void
      {
         StartUpApplicationCommand.offlineRequest(param1);
      }
      
      public function reopenConnection() : void
      {
         // Offline copy: no game-server socket is opened.
      }
      
      public function openConnection(param1:String, param2:int) : void
      {
         // Offline copy: no game-server socket is opened.
      }
      
      public function closeConnection() : void
      {
         // Offline copy: there is no game-server socket to close.
      }
      
      public function connected() : Boolean
      {
         return true;
      }
      
      internal function transmitConnectionEvent(param1:ChannelEvent) : void
      {
         this.sendUpstream(param1);
      }
      
      private function createContext(param1:IChannelHandler) : ChannelHandlerContext
      {
         var _loc2_:ChannelHandlerContext = new ChannelHandlerContext(param1);
         _loc2_.upstreamCallback = this.sendNextUpstreamHandler;
         _loc2_.downstreamCallback = this.sendNextDownstreamHandler;
         return _loc2_;
      }
      
      private function destroyContext(param1:IChannelHandler) : void
      {
         var _loc3_:ChannelHandlerContext = null;
         var _loc2_:IIterator = this._contexts.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(_loc3_.handler == param1)
            {
               this._contexts.removeItem(_loc3_);
               return;
            }
         }
      }
      
      private function sendEventDownstream(param1:ChannelEvent, param2:IListPointer = null) : Boolean
      {
         var _loc3_:ChannelHandlerContext = this.getNextDownstreamHandlerContext(param2);
         if(_loc3_ == null)
         {
            this._sink.handleDownstream(param1);
            return false;
         }
         var _loc4_:IChannelDownstreamHandler = _loc3_.handler as IChannelDownstreamHandler;
         _loc4_.handleDownstream(_loc3_,param1);
         return true;
      }
      
      private function sendUpstream(param1:ChannelEvent, param2:IListPointer = null) : void
      {
         var _loc3_:ChannelHandlerContext = this.getNextUpstreamHandlerContext(param2);
         if(_loc3_ == null)
         {
            return;
         }
         var _loc4_:IChannelUpstreamHandler = _loc3_.handler as IChannelUpstreamHandler;
         _loc4_.handleUpstream(_loc3_,param1);
      }
      
      private function sendNextUpstreamHandler(param1:ChannelEvent, param2:ChannelHandlerContext) : void
      {
         var _loc3_:IListPointer = this._contexts.getPointer(param2);
         if(!_loc3_.next())
         {
            return;
         }
         this.sendUpstream(param1,_loc3_);
      }
      
      private function sendNextDownstreamHandler(param1:ChannelEvent, param2:ChannelHandlerContext) : void
      {
         var _loc3_:IListPointer = this._contexts.getPointer(param2);
         this.sendEventDownstream(param1,_loc3_);
      }
      
      private function getNextUpstreamHandlerContext(param1:IListPointer = null) : ChannelHandlerContext
      {
         var _loc3_:ChannelHandlerContext = null;
         if(this._contexts.numItems == 0)
         {
            return null;
         }
         var _loc2_:IListPointer = param1;
         if(_loc2_ == null)
         {
            _loc2_ = this._contexts.getPointer();
            _loc2_.rewind();
         }
         while(true)
         {
            _loc3_ = _loc2_.getCurrent() as ChannelHandlerContext;
            if(_loc3_.handler.canHandleUpstream())
            {
               break;
            }
            if(!_loc2_.next())
            {
               return null;
            }
         }
         return _loc3_;
      }
      
      private function getNextDownstreamHandlerContext(param1:IListPointer = null) : ChannelHandlerContext
      {
         var _loc3_:ChannelHandlerContext = null;
         if(this._contexts.numItems == 0)
         {
            return null;
         }
         if(param1 != null && !param1.previous())
         {
            return null;
         }
         var _loc2_:IListPointer = param1;
         if(_loc2_ == null)
         {
            _loc2_ = this._contexts.getPointer(this._contexts.getLastItem());
         }
         while(true)
         {
            _loc3_ = _loc2_.getCurrent() as ChannelHandlerContext;
            if(_loc3_.handler.canHandleDownstream())
            {
               break;
            }
            if(!_loc2_.previous())
            {
               return null;
            }
         }
         return _loc3_;
      }
      
      private function getChannelHandlerContextPointer(param1:IChannelHandler) : IListPointer
      {
         var _loc3_:ChannelHandlerContext = null;
         var _loc2_:IIterator = this._contexts.getIterator();
         while(_loc2_.hasNext())
         {
            _loc3_ = _loc2_.getNext();
            if(_loc3_.handler == param1)
            {
               return this._contexts.getPointer(_loc3_);
            }
         }
         return null;
      }
   }
}

