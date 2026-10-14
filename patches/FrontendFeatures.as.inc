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
         replayControls.graphics.beginFill(0xf7f3d2,.95);replayControls.graphics.drawRoundRect(0,0,740,34,8);replayControls.graphics.endFill();
         serverAction(replayControls,"Pause / resume",5,3,145,function():void {
            if(!mockActive)return;replayPaused=!replayPaused;replayApplyTiming();replayUpdateLabel();mockStatus(replayPaused ? "Replay paused" : "Replay resumed");
         });
         serverAction(replayControls,"Speed",160,3,80,function():void {
            if(!mockActive)return;var speeds:Array=[.5,1,2,4];replaySpeed=Number(speeds[(speeds.indexOf(replaySpeed)+1)%speeds.length]);replayApplyTiming();replayUpdateLabel();mockStatus("Replay speed " + replaySpeed);
         });
         serverAction(replayControls,"Previous turn",250,3,135,function():void { replaySeek(replayCurrentTurn-1); });
         serverAction(replayControls,"Next turn",395,3,120,function():void { replaySeek(replayCurrentTurn+1); });
         replayLabel=serverText(replayControls,"",525,4,210);replayUpdateLabel();
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
            serverText(serverPanel,"Glory: " + data.wallet.glory + "   Influence: " + data.wallet.influence + "   Coins: " + data.wallet.coins,20,50,740);
            serverText(serverPanel,data.free_customization ? "Free customization: claim cosmetics at no cost." : "Spend tournament rewards on cosmetic palettes.",20,85,740);
            var y:int=125;
            for each(var item:Object in data.catalog) {
               var costs:Array=[];for(var currency:String in item.price) costs.push(item.price[currency] + " " + currency);
               serverText(serverPanel,item.name + (item.owned ? " (owned)" : "") + "   " + (costs.length ? costs.join(", ") : "free"),20,y,490);
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
            var lines:Array=["League: " + names[data.ranking.league] + "   Rating: " + data.rating,"Qualifying ranked games: " + data.qualifying_games];
            for each(var tier:Object in data.leagues)lines.push(names[tier.id] + ": " + tier.min_rating + " rating");
            lines.push(data.season != null ? "Season " + data.season : "Seasons disabled");
            for each(var old:Object in data.season_history)lines.push("Season " + old.season + ": " + old.rating + " rating / W " + old.wins + " D " + old.draws + " L " + old.defeats);
            var text:TextField=serverText(serverPanel,lines.join("\n"),20,55,730);text.multiline=true;text.height=330;
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
            var lines:Array=[];
            for each(var report:Object in data.reports)lines.push("Report #" + report.id + " " + report.target + ": " + report.reason);
            for each(var sanction:Object in data.sanctions)lines.push(sanction.nickname + " / " + sanction.kind + " / " + sanction.reason);
            for each(var entry:Object in data.audit)lines.push("Audit " + entry.action + ": " + entry.target_name + " / " + entry.reason);
            var text:TextField=serverText(serverPanel,lines.length ? lines.join("\n") : "No reports or sanctions.",20,225,750);text.multiline=true;text.height=180;text.mouseWheelEnabled=true;
         });
      }
