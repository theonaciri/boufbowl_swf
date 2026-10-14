      public static function tracePowerNumber(actor:String,value:int):void { serverTrace("Power display " + actor + " delta=" + value); }
      public static function setMatchToolbar(active:Boolean):void {
         if(serverInMatch != active)serverTrace(active ? "Match toolbar hidden" : "Match toolbar shown");
         serverInMatch=active;
         if(toolbar != null)toolbar.visible=!active;
      }
      public static function filterBallCutscenes(message:com.ankamagames.boufbowl.protocol.ResolutionScenarioMessage):void {
         var entries:Array=message.interaction.concat();
         entries.sort(function(a:Object,b:Object):Number {
            var ticks:Number=a.interactionDetails.startTick-b.interactionDetails.startTick;
            return ticks != 0 ? ticks : a.interactionId-b.interactionId;
         });
         var shown:Object={};var kept:int=0;var suppressed:int=0;
         for each(var entry:Object in entries) {
            var details:Object=entry.interactionDetails;var kind:int=int(details.type);
            var ballAction:Boolean=kind==12 || kind==13 || kind==14 || kind==15 || kind==17 || kind==21;
            if(kind==20)for each(var participant:Object in details.participants) if(participant.hasBall)ballAction=true;
            var category:int=kind==17 ? 12 : kind;
            if(details.isCutscene) {
               if(ballAction && !shown[category]) { shown[category]=true;kept++; }
               else { details.isCutscene=false;suppressed++; }
            }
         }
         serverTrace("Action cinematics: turn " + message.turn + " kept=" + kept + " suppressed=" + suppressed);
      }
      private static function serverCaption(text:String):String {
         var labels:Object=@LOCAL_UI@;
         var lang:String=AccountInformations(app.contextInjector.getInstance(AccountInformations)).lang;
         if(labels[text] != null)return String(labels[text][lang] || text);
         var colon:int=text.indexOf(": ");
         if(colon>0 && labels[text.substring(0,colon)] != null)return serverCaption(text.substring(0,colon))+": "+serverCaption(text.substring(colon+2));
         return text;
      }
      private static function serverFrame(parent:Sprite,x:int,y:int,width:int,height:int):void {
         var template:com.ankamagames.boufbowl.client.components.MessageBoxResizableTextUI=new com.ankamagames.boufbowl.client.components.MessageBoxResizableTextUI();
         var skin:flash.display.MovieClip=template.textBackgroundInstance;
         template.removeChild(skin);skin.width=width;skin.height=height;skin.x=x;skin.y=y;
         skin.mouseEnabled=false;skin.mouseChildren=false;parent.addChild(skin);
         var bounds:flash.geom.Rectangle=skin.getBounds(parent);skin.x+=x-bounds.x;skin.y+=y-bounds.y;
      }
      private static function serverHeading(parent:Sprite,title:String,x:int,y:int,width:int):TextField {
         var field:TextField=serverText(parent,title,x,y,width);
         var format:TextFormat=field.defaultTextFormat;format.font="Copperplate Gothic Bold";format.bold=false;format.size=17;format.color=0x738c38;
         field.defaultTextFormat=format;field.text=serverCaption(title);field.height=32;return field;
      }
      private static function serverRows(parent:Sprite,x:int,y:int,width:int,height:int,step:int):void {
         var rows:Sprite=new Sprite();rows.x=x;rows.y=y;rows.mouseEnabled=false;rows.mouseChildren=false;
         for(var i:int=0;i<height/step;i++) {
            rows.graphics.beginFill(i%2==0 ? 0xf0eccb : 0xfffcec,.85);
            rows.graphics.drawRect(0,i*step,width,Math.min(step,height-i*step));rows.graphics.endFill();
         }
         parent.addChild(rows);
      }
      private static function serverRewardBalance(parent:Sprite,wallet:Object):void {
         var classes:Array=[com.ankamagames.boufbowl.client.components.matchmaking.rewards.BowltonGold,com.ankamagames.boufbowl.client.components.matchmaking.rewards.BowltonIron,com.ankamagames.boufbowl.client.components.matchmaking.rewards.BowltonCopper];
         var keys:Array=["glory","influence","coins"];var labels:Array=["Glory","Influence","Coins"];
         for(var i:int=0;i<3;i++) {
            var type:Class=classes[i];var icon:flash.display.DisplayObject=new type();icon.width=26;icon.height=26;parent.addChild(icon);
            var bounds:flash.geom.Rectangle=icon.getBounds(parent);icon.x+=24+i*245-bounds.x;icon.y+=51-bounds.y;
            serverText(parent,serverCaption(labels[i])+"  " + wallet[keys[i]],60+i*245,55,170);
         }
      }
      private static function serverPalettePreview(parent:Sprite,item:Object,x:int,y:int):void {
         var palettes:Object=@COSMETIC_PALETTES@;
         var colors:Array=palettes[item.kind+":"+item.asset_id];if(colors == null)return;
         var preview:Sprite=new Sprite();preview.x=x;preview.y=y;preview.mouseEnabled=false;
         for(var i:int=0;i<Math.min(5,colors.length);i++) {
            preview.graphics.lineStyle(1,0x82764e);preview.graphics.beginFill(parseInt(String(colors[i]),16));
            preview.graphics.moveTo(i*17+8,0);preview.graphics.lineTo(i*17+15,4);preview.graphics.lineTo(i*17+15,12);
            preview.graphics.lineTo(i*17+8,16);preview.graphics.lineTo(i*17+1,12);preview.graphics.lineTo(i*17+1,4);
            preview.graphics.lineTo(i*17+8,0);preview.graphics.endFill();
         }
         parent.addChild(preview);
      }
      public static var serverTournamentRounds:Object={};
      public static function serverTournamentDetails(id:Object):Object { return serverTournamentRounds[serverId(id)]; }
      private static var serverRole:String = "player";
      private static var replayRoot:Object;
      private static var replayPaused:Boolean = false;
      private static var replaySpeed:Number = 1;
      private static var replayCurrentTurn:int = 1;
      private static var replayPauseAfterSeek:Boolean=false;
      private static var replayControls:Sprite;
      private static var replayLabel:TextField;

      private static function replayResetControls():void {
         com.ankamagames.boufbowl.resolution.display.script.runner.AsvmTimeProvider.configure(1,false);
         if(replayControls != null && replayControls.parent != null) replayControls.parent.removeChild(replayControls);
         replayControls=null;replayLabel=null;replayPaused=false;
      }
      private static function replayApplyTiming():void {
         clearTimeout(mockTimeout);
         if(!replayPaused && mockWaiting != null) mockTimeout=setTimeout(function():void { if(mockActive && mockWaiting != null) mockFailure("Timed out waiting for " + mockWaiting); },int(90000/Math.min(1,replaySpeed)));
         com.ankamagames.boufbowl.resolution.display.script.runner.AsvmTimeProvider.configure(replaySpeed,replayPaused);
         var controller:com.ankamagames.boufbowl.resolution.display.script.runner.SceneController = com.ankamagames.boufbowl.resolution.display.script.runner.SceneController.active;
         if(controller != null) controller.applyReplayTiming();
      }
      private static function replayUpdateLabel():void {
         if(replayLabel != null) replayLabel.text="Turn " + replayCurrentTurn + " / " + replaySpeed + "x" + (replayPaused ? " / paused" : "");
      }
      private static function replayBuildControls():void {
         replayControls=new Sprite();replayControls.x=10;replayControls.y=530;
         serverFrame(replayControls,0,0,800,36);
         serverAction(replayControls,"Pause / resume",5,3,145,function():void {
            if(!mockActive)return;replayPaused=!replayPaused;replayApplyTiming();replayUpdateLabel();mockStatus(replayPaused ? "Replay paused" : "Replay resumed");
         });
         serverAction(replayControls,"Speed",160,3,80,function():void {
            if(!mockActive)return;var speeds:Array=[.5,1,2,4];replaySpeed=Number(speeds[(speeds.indexOf(replaySpeed)+1)%speeds.length]);replayApplyTiming();replayUpdateLabel();mockStatus("Replay speed " + replaySpeed);
         });
         serverAction(replayControls,"Previous turn",250,3,135,function():void { replaySeek(replayCurrentTurn-1); });
         serverAction(replayControls,"Next turn",395,3,120,function():void { replaySeek(replayCurrentTurn+1); });
         serverAction(replayControls,"Exit replay",525,3,125,function():void { stopMock();showHome(); });
         replayLabel=serverText(replayControls,"",655,4,140);replayUpdateLabel();
         Stage(app.contextInjector.getInstance(Stage)).addChild(replayControls);
      }
      private static function replaySeek(turn:int):void {
         if(replayRoot == null || !mockActive)return;
         var steps:Array=replayRoot.steps;var fieldIndex:int=-1;
         for(var i:int=0;i<steps.length;i++)
            if(steps[i].type == "FIELD_STATE" && i+1<steps.length && steps[i+1].type == "RESOLUTION_SCENARIO" && int(steps[i].decoded.teamState.turn)==turn) { fieldIndex=i;break; }
         if(fieldIndex<0)return;
         var masks:Object={};if(replayRoot.chapters != null) for each(var chapter:Object in replayRoot.chapters) if(int(chapter.turn)==turn && chapter.zobal_masks != null) masks=chapter.zobal_masks;
         var paused:Boolean=replayPaused;var speed:Number=replaySpeed;
         stopMock();showHome();serverZobalMasks=masks;
         var selected:Object=com.adobe.serialization.json.JSON.decode(com.adobe.serialization.json.JSON.encode(replayRoot));
         var field:Object=selected.steps[fieldIndex];delete field.wait_for;field.after_ms=300;
         selected.steps=[selected.steps[0],field].concat(selected.steps.slice(fieldIndex+1));
         selected.steps[0].after_ms=0;
         mockFixture=selected;mockIndex=0;mockActive=true;replayCurrentTurn=turn;replaySpeed=speed;replayPaused=false;replayPauseAfterSeek=paused;
         replayApplyTiming();replayBuildControls();scheduleMockStep();mockStatus("Replay seeking turn " + turn);
      }

      private static function serverWalletPanel():void {
         serverCommunityRequest({action:"wallet"},function(data:Object):void {
            serverDialog("Wallet and cosmetic collection",440);serverTrace("Wallet opened");
            serverRewardBalance(serverPanel,data.wallet);
            serverText(serverPanel,data.free_customization ? "Free customization: claim cosmetics at no cost." : "Spend tournament rewards on cosmetic palettes.",20,85,740);
            serverRows(serverPanel,20,121,740,210,35);
            var y:int=125;
            for each(var item:Object in data.catalog) {
               var costs:Array=[];for(var currency:String in item.price) costs.push(item.price[currency] + " " + serverCaption(currency));
               serverPalettePreview(serverPanel,item,30,y+6);
               serverText(serverPanel,serverCaption(item.name) + (item.owned ? "  ("+serverCaption("Owned")+")" : ""),130,y+2,260);
               serverText(serverPanel,costs.length ? costs.join(", ") : serverCaption("Free"),385,y+2,200);
               if(!item.owned) {
                  (function(identity:String,row:int):void {
                     serverAction(serverPanel,data.free_customization ? "Claim" : "Buy",590,row,150,function():void { serverCommunityRequest({action:"buy",item_id:identity},function(result:Object):void { serverWalletPanel(); }); });
                  })(String(item.id),y);
               }
               y+=35;
            }
            serverAction(serverPanel,"Award / purchase history",20,365,260,function():void {
               serverDialog("Wallet history",420);var lines:Array=[];
               for each(var award:Object in data.awards)lines.push("Tournament " + award.tournament + ": " + award.amount.glory + " G / " + award.amount.influence + " I / " + award.amount.coins + " C");
               for each(var purchase:Object in data.purchases)lines.push("Cosmetic: " + purchase.item);
               var text:TextField=serverText(serverPanel,lines.length ? lines.join("\n") : "No awards or purchases yet.",20,55,750);text.multiline=true;text.height=320;text.mouseWheelEnabled=true;
            });
         });
      }
      private static function serverProgressionPanel():void {
         serverCommunityRequest({action:"progression"},function(data:Object):void {
            serverDialog("Ranked progression",420);serverTrace("Progression opened");
            var names:Object={1:"Craqueleur",2:"Abraknyde",3:"Wabbit",4:"Tofu",5:"Piou",0:"Unranked"};
            serverText(serverPanel,"Rating: " + data.rating + "   /   " + names[data.ranking.league],20,50,730);
            serverText(serverPanel,"Qualifying ranked games: " + data.qualifying_games,20,78,730);
            var row:int=113;serverRows(serverPanel,20,row,740,190,38);
            for each(var tier:Object in data.leagues) {
               var cube:com.ankamagames.boufbowl.client.components.league.LeagueCubeUI=new com.ankamagames.boufbowl.client.components.league.LeagueCubeUI();
               cube.league=int(tier.id);cube.width=30;cube.height=32;serverPanel.addChild(cube);var bounds:flash.geom.Rectangle=cube.getBounds(serverPanel);cube.x+=32-bounds.x;cube.y+=row+3-bounds.y;
               var caption:TextField=serverText(serverPanel,names[tier.id],85,row+8,230);
               serverText(serverPanel,String(tier.min_rating) + "+",340,row+8,140);
               if(int(data.ranking.league)==int(tier.id))serverText(serverPanel,serverCaption("Your league"),560,row+8,170);
               row+=38;
            }
            serverText(serverPanel,data.season != null ? "Season " + data.season : "Seasons disabled",20,317,730);
            var lines:Array=[];
            for each(var old:Object in data.season_history)lines.push("Season " + old.season + ": " + old.rating + " / W " + old.wins + " D " + old.draws + " L " + old.defeats);
            var text:TextField=serverText(serverPanel,lines.join("\n"),20,346,730);text.multiline=true;text.height=60;text.mouseWheelEnabled=true;

         });
      }
      private static function serverNewsPanel():void {
         serverCommunityRequest({action:"news"},function(data:Object):void {
            serverDialog("News",440);serverTrace("News opened");
            var content:String=String(data.body);
            if(data.running_tournament != null)content+="<br /><br />Running tournament: " + data.running_tournament;
            if(data.next_tournament != null)content+="<br />Next tournament: " + new Date(Number(data.next_tournament.start_time)*1000).toLocaleString();
            var motd:com.ankamagames.boufbowl.client.components.login.LoginMotdUI=new com.ankamagames.boufbowl.client.components.login.LoginMotdUI();
            motd.setText("<span color='#463d2b'>" + String(data.title) + "</span>","<span color='#463d2b' fontSize='14'>" + content + "</span>");motd.x=25;motd.y=55;serverPanel.addChild(motd);
            if(motd.width>730)motd.scaleX=730/motd.width;
            if(motd.height>340)motd.scaleY=340/motd.height;
         });
      }
      private static function serverModerationPanel():void {
         serverCommunityRequest({action:"moderation"},function(data:Object):void {
            serverDialog("Moderation: " + data.role,440);serverTrace("Moderation opened");
            serverText(serverPanel,"Player nickname",20,50,160);var target:TextField=serverInput(serverPanel,"",190,50,550);
            serverText(serverPanel,"Reason",20,90,160);var reason:TextField=serverInput(serverPanel,"",190,90,550);
            serverText(serverPanel,"Duration (seconds)",20,130,170);var duration:TextField=serverInput(serverPanel,"900",190,130,150);
            var verbs:Array=["kick","ban","mute","unban","unmute"];
            for(var i:int=0;i<verbs.length;i++) {
               (function(verb:String,index:int):void {
                  serverAction(serverPanel,verb,20+index*150,175,140,function():void {
                     serverCommunityRequest({action:"moderate",nickname:target.text,verb:verb,duration:verb == "kick" ? 30 : int(duration.text),reason:reason.text},function(result:Object):void { serverModerationPanel(); });
                  });
               })(String(verbs[i]),i);
            }
            serverRows(serverPanel,20,265,750,140,28);
            var text:TextField=serverText(serverPanel,"",25,265,740);text.multiline=true;text.wordWrap=true;text.height=140;text.mouseWheelEnabled=true;text.selectable=true;
            var render:Function=function(kind:String):void {
               var lines:Array=[];
               if(kind=="Reports") for each(var report:Object in data.reports)lines.push("#"+report.id+"  "+report.target+" - "+report.reason);
               if(kind=="Sanctions") for each(var sanction:Object in data.sanctions)lines.push(sanction.nickname+" / "+serverCaption(sanction.kind)+" - "+sanction.reason);
               if(kind=="Audit") for each(var entry:Object in data.audit)lines.push(serverCaption(entry.action)+": "+entry.target_name+" - "+entry.reason);
               text.text=lines.length ? lines.join("\n") : serverCaption("No entries");text.scrollV=1;
            };
            var sections:Array=["Reports","Sanctions","Audit"];
            for(var section:int=0;section<sections.length;section++) {
               (function(kind:String,index:int):void { serverAction(serverPanel,kind,20+index*255,225,240,function():void { render(kind); }); })(sections[section],section);
            }
            render(data.reports.length ? "Reports" : data.sanctions.length ? "Sanctions" : "Audit");

         });
      }
