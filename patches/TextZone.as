package com.ankamagames.xgaming.ui.components
{
   import com.ankamagames.xgaming.utils.display.Color3;
   import com.ankamagames.xgaming.utils.logging.LoggerFactory;
   import com.ankamagames.xgaming.utils.string.StringUtils;
   import com.reider.log4AS3.ILogger;
   import flash.display.DisplayObject;
   import flash.display.DisplayObjectContainer;
   import flash.display.Sprite;
   import flash.geom.Rectangle;
   import com.ankamagames.boufbowl.BoufbowlClient;
   import flash.errors.IllegalOperationError;
   import flash.events.Event;
   import flash.system.ApplicationDomain;
   import flash.text.engine.FontLookup;
   import flash.text.engine.FontWeight;
   import flash.text.engine.RenderingMode;
   import flash.text.engine.TextBaseline;
   import flash.text.engine.TextLine;
   import flashx.textLayout.tlf_internal;
   import flashx.textLayout.compose.TextFlowLine;
   import flashx.textLayout.container.ContainerController;
   import flashx.textLayout.conversion.ITextImporter;
   import flashx.textLayout.conversion.TextConverter;
   import flashx.textLayout.elements.Configuration;
   import flashx.textLayout.elements.InlineGraphicElement;
   import flashx.textLayout.elements.ParagraphElement;
   import flashx.textLayout.elements.TextFlow;
   import flashx.textLayout.events.TextLayoutEvent;
   import flashx.textLayout.formats.ITextLayoutFormat;
   import flashx.textLayout.formats.TextDecoration;
   import flashx.textLayout.formats.TextLayoutFormat;

   use namespace tlf_internal;

   public class TextZone extends Sprite implements IScrollableContent
   {
      public var webParagraphLayout:Boolean = false;

      private static const DEFAULT_WIDTH:Number = 300;

      private static const DEFAULT_HEIGHT:Number = 300;

      private static const LOGGER:ILogger = LoggerFactory.getLogger(TextZone);

      private var _graphicHMargin:Number;

      private var _paddings:Padding;

      private var _defaultFontFamily:String;

      private var _defaultFontSize:int;

      private var _defaultTextColor:Color3;

      private var _defaultTextAlign:String;

      private var _linkNormalFormatColor:Color3;

      private var _linkHoverFormatColor:Color3;

      private var _width:Number;

      private var _height:Number;

      private var _allowScrollDispatching:Boolean;

      private var _controller:ContainerController;

      private var _textFlow:TextFlow;

      private var _importer:ITextImporter;

      private var _graphicElements:Vector.<Function>;

      private var _scrollRatio:Number;

      private var _textUpdatePending:Boolean = false;

      private var _compositionFailed:Boolean = false;

      public function TextZone(param1:Number = 5)
      {
         super();
         this.init(param1);
      }

      public function get defaultFontFamily() : String
      {
         return this._defaultFontFamily;
      }

      public function set defaultFontFamily(param1:String) : void
      {
         this._defaultFontFamily = param1;
      }

      public function get defaultFontSize() : int
      {
         return this._defaultFontSize;
      }

      public function set defaultFontSize(param1:int) : void
      {
         this._defaultFontSize = param1;
      }

      public function get defaultTextColor() : Color3
      {
         return this._defaultTextColor;
      }

      public function set defaultTextColor(param1:Color3) : void
      {
         this._defaultTextColor = param1;
      }

      public function get defaultTextAlign() : String
      {
         return this._defaultTextAlign;
      }

      public function set defaultTextAlign(param1:String) : void
      {
         this._defaultTextAlign = param1;
      }

      public function get linkNormalFormatColor() : Color3
      {
         return this._linkNormalFormatColor;
      }

      public function set linkNormalFormatColor(param1:Color3) : void
      {
         this._linkNormalFormatColor = param1;
      }

      public function get linkHoverFormatColor() : Color3
      {
         return this._linkHoverFormatColor;
      }

      public function set linkHoverFormatColor(param1:Color3) : void
      {
         this._linkHoverFormatColor = param1;
      }

      public function get scrollRatio() : Number
      {
         return this._scrollRatio;
      }

      public function set scrollRatio(param1:Number) : void
      {
         if(param1 < 0)
         {
            this.applyScrollRatio(0);
         }
         else if(param1 > 1)
         {
            this.applyScrollRatio(1);
         }
         else
         {
            this.applyScrollRatio(param1);
         }
      }

      public function get viewportRatio() : Number
      {
         if(this._controller == null) return 1;
         var contentHeight:Number = this._controller.getContentBounds().height;
         return isFinite(contentHeight) && contentHeight > 0 ?
            Math.min(1,this._controller.compositionHeight / contentHeight) : 1;
      }

      public function get preferedScrollStepRatio() : Number
      {
         if(this._controller == null) return 0;
         var extent:Number = this._controller.getContentBounds().height - this._controller.compositionHeight;
         return isFinite(extent) && extent > 0 ? Math.min(1,15 / extent) : 0;
      }

      public function get controller() : ContainerController
      {
         return this._controller;
      }

      public function setPaddings(top:int, right:int, bottom:int, left:int) : void
      {
         if(this._paddings.top == top && this._paddings.right == right &&
            this._paddings.bottom == bottom && this._paddings.left == left) return;
         this._paddings = new Padding(top,right,bottom,left);
         if(this._textFlow)
         {
            this.applyPaddings(this._textFlow);
            this.registerForTextFlowUpdate();
         }
      }

      public function setContent(param1:String, param2:Vector.<Function> = null) : void
      {
         this._graphicElements = param2;
         if(this._textFlow != null)
         {
            this._textFlow.flowComposer.removeAllControllers();
         }
         this._textFlow = this.createTextFlow(this.applyDefaults(param1));
         this._textFlow.linkNormalFormat = this.getLinkFormat(this._linkNormalFormatColor);
         this._textFlow.linkActiveFormat = this._textFlow.linkHoverFormat = this.getLinkFormat(this._linkHoverFormatColor || this._linkNormalFormatColor);
         this._controller = new ContainerController(this,this._width,this._height);
         this._textFlow.flowComposer.addController(this._controller);
         this.registerForTextFlowUpdate();
      }

      public function appendParagraph(param1:ParagraphElement) : void
      {
         if(this._textFlow == null)
         {
            this._textFlow = this.createTextFlow();
            this._controller = new ContainerController(this,this._width,this._height);
            this._textFlow.flowComposer.addController(this._controller);
         }
         this._textFlow.addChild(param1);
         this.registerForTextFlowUpdate();
      }

      public function canScroll() : Boolean
      {
         if(this._controller == null) return false;
         var _loc1_:Number = this._controller.getContentBounds().height;
         var _loc2_:Number = this._controller.compositionHeight;
         return this._controller != null && _loc1_ > _loc2_;
      }

      public function updateNow() : void
      {
         this.updateTextFlow();
      }

      public function updateScroll() : void
      {
         if(this.canScroll())
         {
            this.applyScrollRatio(this._scrollRatio);
         }
         else
         {
            this.applyScrollRatio(0);
         }
      }

      public function setSize(widthValue:Number, heightValue:Number) : void
      {
         var changed:Boolean = this._width != widthValue || this._height != heightValue;
         this._width = widthValue;
         this._height = heightValue;
         if(BoufbowlClient.ruffleRuntime && (changed || scrollRect == null))
            scrollRect = new Rectangle(0,0,widthValue,heightValue);
         if(this._controller != null && changed)
         {
            this._controller.setCompositionSize(this._width,this._height);
            this.registerForTextFlowUpdate();
         }
      }

      private function getLinkFormat(param1:Color3) : ITextLayoutFormat
      {
         var _loc2_:TextLayoutFormat = new TextLayoutFormat();
         _loc2_.textDecoration = TextDecoration.UNDERLINE;
         if(param1 != null)
         {
            _loc2_.color = param1.toRgbInt();
         }
         return _loc2_;
      }

      private function applyDefaults(param1:String) : String
      {
         var _loc2_:String = "<TextFlow xmlns=\"http://ns.adobe.com/textLayout/2008\" version=\"2.0.0\"";
         if(this._defaultFontFamily != null && this._defaultFontFamily.length != 0)
         {
            _loc2_ += " fontFamily=\"" + StringUtils.htmlEscape(this._defaultFontFamily) + "\"";
         }
         if(this._defaultFontSize > 0)
         {
            _loc2_ += " fontSize=\"" + this._defaultFontSize + "\"";
         }
         if(this._defaultTextColor != null)
         {
            _loc2_ += " color=\"#" + this._defaultTextColor.toRgbHexaString() + "\"";
         }
         if(this._defaultTextAlign != null && this._defaultTextAlign.length != 0)
         {
            _loc2_ += " textAlign=\"" + this._defaultTextAlign + "\"";
         }
         return _loc2_ + (">" + param1 + "</TextFlow>");
      }

      private function registerForTextFlowUpdate(event:Event = null) : void
      {
         // Every runtime composes a batch only once on its next frame. Explicit
         // updateNow() remains synchronous and cancels this pending update.
         if(this._textUpdatePending) return;
         this._textUpdatePending = true;
         addEventListener(Event.ENTER_FRAME,this.textUpdate,false,0,true);
      }

      private function applyPaddings(param1:TextFlow) : void
      {
         param1.paddingTop = this._paddings.top;
         param1.paddingRight = this._paddings.right;
         param1.paddingBottom = this._paddings.bottom;
         param1.paddingLeft = this._paddings.left;
      }

      private function createTextFlow(param1:String = null) : TextFlow
      {
         var _loc2_:TextFlow = null;
         if(param1 == null)
         {
            _loc2_ = new TextFlow();
         }
         else
         {
            _loc2_ = this._importer.importToFlow(param1);
         }
         _loc2_.fontLookup = FontLookup.EMBEDDED_CFF;
         _loc2_.renderingMode = RenderingMode.CFF;
         _loc2_.fontWeight = FontWeight.NORMAL;
         this.applyPaddings(_loc2_);
         _loc2_.addEventListener(TextLayoutEvent.SCROLL,this.textFlowScrollHandler,false,0,true);
         this._allowScrollDispatching = true;
         return _loc2_;
      }

      private function textFlowScrollHandler(param1:TextLayoutEvent) : void
      {
         if(this._allowScrollDispatching)
         {
            dispatchEvent(new Event(Event.CHANGE));
         }
      }

      private function updateTextFlow() : void
      {
         if(!this._textUpdatePending && !this._compositionFailed) return;
         this._textUpdatePending = false;
         this._compositionFailed = false;
         try
         {
            removeEventListener(Event.ENTER_FRAME,this.textUpdate);
            if(this._textFlow == null) return;
            this._allowScrollDispatching = false;
            if(this.webParagraphLayout)
            {
               // Ruffle can draw a wrapped paragraph inside a single TextLine
               // while TLF reserves only one baseline. Compose all paragraphs,
               // then stack their actual rendered bounds before clipping.
               this._controller.verticalScrollPosition = 0;
               this._controller.setCompositionSize(this._width,NaN);
               this._textFlow.flowComposer.updateAllControllers();
               this.layoutWebParagraphs();
            }
            else this._textFlow.flowComposer.updateAllControllers();
            this.applyScrollRatio(this._scrollRatio);
            dispatchEvent(new Event(Event.CHANGE));
         }
         catch(error:Error)
         {
            this._compositionFailed = true;
            this._allowScrollDispatching = true;
            LOGGER.error("TextZone::setContent : {}",error.message);
         }
      }

      private function applyScrollRatio(ratio:Number) : void
      {
         // Empty content must never feed negative or NaN positions into TLF.
         ratio = isNaN(ratio) ? 0 : Math.max(0,Math.min(1,ratio));
         this._scrollRatio = ratio;
         this._allowScrollDispatching = false;
         if(this._controller != null)
         {
            var extent:Number = this._controller.getContentBounds().height - this._controller.compositionHeight;
            var offset:Number = ratio * (isFinite(extent) ? Math.max(0,extent) : 0);
            if(this.webParagraphLayout) scrollRect = new Rectangle(0,offset,this._width,this._height);
            else this._controller.verticalScrollPosition = offset;
         }
         this._allowScrollDispatching = true;
      }

      private function collectWebLines(container:DisplayObjectContainer, lines:Array) : void
      {
         for(var i:int=0;i<container.numChildren;i++)
         {
            var child:DisplayObject = container.getChildAt(i);
            if(child is TextLine) lines.push(child);
            else if(child is DisplayObjectContainer) this.collectWebLines(DisplayObjectContainer(child),lines);
         }
      }

      private function layoutWebParagraphs() : void
      {
         var lines:Array = [];
         this.collectWebLines(this,lines);
         lines.sortOn("y",Array.NUMERIC);
         var bottom:Number = this._paddings.top;
         for(var i:int=0;i<lines.length;i++)
         {
            var line:TextLine = TextLine(lines[i]);
            // Importing empty content creates a leading placeholder paragraph.
            if(i == 0 && line.textBlock != null && /^\s*$/.test(line.textBlock.content.rawText))
            {
               line.visible = false;
               continue;
            }
            line.visible = true;
            var bounds:Rectangle = line.getBounds(this);
            var delta:Number = bottom - bounds.y;
            var lineHeight:Number = Math.max(bounds.height,line.ascent + line.descent);
            line.y += delta;
            var model:TextFlowLine = line.userData as TextFlowLine;
            if(model != null) model.setXYAndHeight(model.x,model.y + delta,lineHeight);
            bottom += lineHeight;
         }
         this._controller.setCompositionSize(this._width,this._height);
         this._controller.setContentBounds(0,0,this._width,bottom + this._paddings.bottom);
      }

      private function init(param1:Number) : void
      {
         this._graphicHMargin = param1;
         this._width = DEFAULT_WIDTH;
         this._height = DEFAULT_HEIGHT;
         var _loc2_:Configuration = new Configuration();
         _loc2_.inlineGraphicResolverFunction = this.graphicResolverHandler;
         this._importer = TextConverter.getImporter(TextConverter.TEXT_LAYOUT_FORMAT,_loc2_);
         this._scrollRatio = 0;
         this._paddings = new Padding(0,0,0,0);
      }

      private function textUpdate(event:Event) : void
      {
         this.updateTextFlow();
      }

      private function graphicResolverHandler(param1:InlineGraphicElement) : *
      {
         var _loc5_:DisplayObject = null;
         var _loc6_:Class = null;
         var _loc7_:Number = NaN;
         var _loc2_:String = param1.source as String;
         if(_loc2_ == null)
         {
            throw new IllegalOperationError("Source should be a string");
         }
         if(param1.alignmentBaseline == null)
         {
            param1.alignmentBaseline = TextBaseline.DESCENT;
         }
         var _loc3_:RegExp = /{(.*)?}/ig;
         var _loc4_:Array = _loc3_.exec(_loc2_);
         if(_loc4_ != null)
         {
            if(ApplicationDomain.currentDomain.hasDefinition(_loc4_[1]))
            {
               _loc6_ = ApplicationDomain.currentDomain.getDefinition(_loc4_[1]) as Class;
               if(_loc6_ != null)
               {
                  try
                  {
                     _loc5_ = new _loc6_();
                     return this.wrapWithHMargin(_loc5_,this._graphicHMargin);
                  }
                  catch(error:Error)
                  {
                  }
               }
            }
         }
         _loc3_ = /\[([0-9]+)\]/ig;
         _loc4_ = _loc3_.exec(_loc2_);
         if(_loc4_ != null && this._graphicElements != null)
         {
            _loc7_ = parseInt(_loc4_[1]);
            if(_loc7_ < this._graphicElements.length)
            {
               _loc5_ = this._graphicElements[_loc7_]();
               return this.wrapWithHMargin(_loc5_,this._graphicHMargin);
            }
         }
         return _loc2_;
      }

      private function wrapWithHMargin(param1:DisplayObject, param2:Number) : Sprite
      {
         var _loc3_:Sprite = new Sprite();
         _loc3_.graphics.beginFill(0,0);
         _loc3_.graphics.drawRect(0,0,param1.width + 2 * param2,param1.height);
         _loc3_.graphics.endFill();
         param1.x = param2;
         _loc3_.addChild(param1);
         return _loc3_;
      }
   }
}
