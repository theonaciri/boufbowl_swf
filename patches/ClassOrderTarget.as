package com.ankamagames.boufbowl.protocol
{
   import com.netease.protobuf.Int64;
   import com.netease.protobuf.Message;
   import com.netease.protobuf.ReadUtils;
   import com.netease.protobuf.Tag;
   import com.netease.protobuf.WireType;
   import com.netease.protobuf.WriteUtils;
   import flash.errors.IOError;
   import flash.utils.IDataInput;
   import flash.utils.IDataOutput;
   import flash.utils.IExternalizable;
   
   public final class ClassOrderTarget extends Message implements IExternalizable
   {
      
      public var boufbowlerId:Int64;

      public var effectDeltas:Array = [];
      
      private var preResolutionHitPointsDelta_:int;
      
      private var hasPreResolutionHitPointsDelta_:Boolean = false;
      
      private var postResolutionHitPointsDelta_:int;
      
      private var hasPostResolutionHitPointsDelta_:Boolean = false;
      
      public function ClassOrderTarget()
      {
         super();
      }
      
      public function get hasPreResolutionHitPointsDelta() : Boolean
      {
         return this.hasPreResolutionHitPointsDelta_;
      }
      
      public function set preResolutionHitPointsDelta(param1:int) : void
      {
         this.hasPreResolutionHitPointsDelta_ = true;
         this.preResolutionHitPointsDelta_ = param1;
      }
      
      public function get preResolutionHitPointsDelta() : int
      {
         return this.preResolutionHitPointsDelta_;
      }
      
      public function get hasPostResolutionHitPointsDelta() : Boolean
      {
         return this.hasPostResolutionHitPointsDelta_;
      }
      
      public function set postResolutionHitPointsDelta(param1:int) : void
      {
         this.hasPostResolutionHitPointsDelta_ = true;
         this.postResolutionHitPointsDelta_ = param1;
      }
      
      public function get postResolutionHitPointsDelta() : int
      {
         return this.postResolutionHitPointsDelta_;
      }
      
      public function writeExternal(param1:IDataOutput) : void
      {
         for each(var effect:int in this.effectDeltas) {
            WriteUtils.writeTag(param1,WireType.VARINT,4);
            WriteUtils.write_TYPE_SINT32(param1,effect);
         }
         WriteUtils.writeTag(param1,WireType.VARINT,1);
         WriteUtils.write_TYPE_INT64(param1,this.boufbowlerId);
         if(this.hasPreResolutionHitPointsDelta)
         {
            WriteUtils.writeTag(param1,WireType.VARINT,2);
            WriteUtils.write_TYPE_SINT32(param1,this.preResolutionHitPointsDelta);
         }
         if(this.hasPostResolutionHitPointsDelta)
         {
            WriteUtils.writeTag(param1,WireType.VARINT,3);
            WriteUtils.write_TYPE_SINT32(param1,this.postResolutionHitPointsDelta);
         }
      }
      
      public function readExternal(param1:IDataInput) : void
      {
         var _loc5_:Tag = null;
         var _loc2_:uint = 0;
         var _loc3_:uint = 0;
         var _loc4_:uint = 0;
         while(param1.bytesAvailable != 0)
         {
            _loc5_ = ReadUtils.readTag(param1);
            switch(_loc5_.number)
            {
               case 1:
                  if(_loc2_ != 0)
                  {
                     throw new IOError("Bad data format.");
                  }
                  _loc2_++;
                  this.boufbowlerId = ReadUtils.read_TYPE_INT64(param1);
                  break;
               case 2:
                  if(_loc3_ != 0)
                  {
                     throw new IOError("Bad data format.");
                  }
                  _loc3_++;
                  this.preResolutionHitPointsDelta = ReadUtils.read_TYPE_SINT32(param1);
                  break;
               case 3:
                  if(_loc4_ != 0)
                  {
                     throw new IOError("Bad data format.");
                  }
                  _loc4_++;
                  this.postResolutionHitPointsDelta = ReadUtils.read_TYPE_SINT32(param1);
                  break;
               case 4:
                  this.effectDeltas.push(ReadUtils.read_TYPE_SINT32(param1));
                  break;
               default:
                  ReadUtils.skip(param1,_loc5_.wireType);
            }
         }
         if(_loc2_ != 1)
         {
            throw new IOError("Bad data format.");
         }
      }
   }
}

