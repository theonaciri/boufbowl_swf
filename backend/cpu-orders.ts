/** Coordinated, deterministic planning from public field state only.
 * No opposing orders, future random draws, or match seed enter this planner.
 */
type Cell = {q: number; r: number};
type Elements = {TERRE: number; FEU: number; AIR: number; EAU: number};
type Run = {actor: any; target: Cell; elements: Elements; path: Cell[]; speed: number; risk: number};
const directions = [[1,0],[1,-1],[0,-1],[-1,0],[-1,1],[0,1]];
const cpuDistance = (a: Cell,b: Cell) => Math.max(Math.abs(a.q-b.q),Math.abs(a.r-b.r),Math.abs(a.q+a.r-b.q-b.r));
const cpuColumn = (p: Cell) => p.q+p.r/2;
const cpuActive = (e: any) => e.hp > 0 && !e.status.knocked_down && !e.status.stunned;
const cpuCellKey = (p: Cell) => `${p.q},${p.r}`;
function cpuRound(p: Cell): Cell {
  let q=Math.round(p.q),r=Math.round(p.r),s=Math.round(-p.q-p.r);
  const dq=Math.abs(q-p.q),dr=Math.abs(r-p.r),ds=Math.abs(s+p.q+p.r);
  if (dq>dr && dq>ds) q=-r-s;
  else if (dr>ds) r=-q-s;
  return {q,r};
}

/** Keep the archive AI as a fallback for historical rules; do not forbid risk. */
export function cpuPlanningConfig(cfg: any): any { return cfg; }

export function prepareCPUOrder(cfg: any, world: any, order: any, settings: any = {}): any {
  if (!cfg.client_ranges || cfg.movement.overextension === undefined) {
    const receivers=new Set(order.actions.filter((a: any)=>a.action_type==='throw').map((a: any)=>a.params.target_entity_id));
    for (const action of order.actions) if (action.action_type==='wait' && receivers.has(action.entity_id))
      action.params.elements={TERRE:0,FEU:0,AIR:2,EAU:1};
    return order;
  }
  const ai=cfg.ai, levelName=settings.level ?? ai.default_level, personalityName=settings.personality ?? ai.default_personality;
  const level=ai.levels[levelName], personality=ai.personalities[personalityName];
  const team=world.entities.filter((e: any)=>e.team_id===order.team_index).sort((a: any,b: any)=>a.id-b.id);
  const available=team.filter(cpuActive), enemies=world.entities.filter((e: any)=>e.team_id!==order.team_index && cpuActive(e)).sort((a: any,b: any)=>a.id-b.id);
  const direction=(order.team_index===0)!==Boolean(world.sides_swapped)?1:-1;
  const goal=cfg.ball.goal_line_half_width ?? 15.5, dt=cfg.tick_system.tick_dt_seconds;
  const slots=cfg.general.actions_per_character;
  const allocation=(names: string[]): Elements => {
    const e: any={TERRE:0,FEU:0,AIR:0,EAU:0};
    for (let i=0;i<slots;i++) e[names[Math.min(i,names.length-1)]]++;
    return e;
  };
  const water=allocation(['EAU']), runner=allocation(['FEU','EAU','EAU']);
  const receive=allocation(['AIR','EAU','EAU']), accurate=allocation(['AIR','AIR','EAU']);
  const brute=allocation(['TERRE','TERRE','EAU']), evade=allocation(['FEU','FEU','EAU']);
  const intercept=allocation(['FEU','FEU','EAU']);
  const width=cfg.pitch.width ?? 2*cfg.pitch.width_half+1, height=cfg.pitch.height ?? 2*cfg.pitch.height_half+1;
  const minColumn=-Math.floor(width/2),minRow=-Math.floor(height/2);
  const inBounds=(p: Cell)=>p.r>=minRow && p.r<minRow+height &&
    p.q+Math.floor(p.r/2)>=minColumn && p.q+Math.floor(p.r/2)<minColumn+width;
  const at=(x: number,r: number): Cell=>cpuRound({q:x-r/2,r});
  const forward=(p: Cell)=>direction*cpuColumn(p);
  const safeRange=(e: Elements)=>e.TERRE*cfg.client_ranges.earth_distance_bonus+e.FEU*cfg.client_ranges.fire_distance_bonus+
    e.AIR*cfg.client_ranges.air_distance_bonus+e.EAU*cfg.client_ranges.water_distance_bonus;
  const speed=(actor: any,e: Elements)=>Math.max(.1,cfg.movement.base_speed_cells_per_sec+actor.stats.endurance*cfg.movement.speed_per_endurance+
    e.EAU*cfg.movement.eau_speed_bonus_per_action+e.AIR*cfg.movement.air_speed_bonus_per_action-e.TERRE*cfg.movement.terre_speed_penalty_per_action);
  const probability=(p: number)=>Math.max(cfg.simulation.probability_min,Math.min(cfg.simulation.probability_max,p));
  const used=new Map<number,Run>(), roles: any[]=[], protectedIds=new Set<number>();
  const reserved=new Set<string>();
  const paths=new Map<number,{target: Cell;path: Cell[]}[]>();
  // Use the engine's neighbour order and occupied starting cells. Predictions
  // remain estimates: opponents may move, fight, or obstruct the planned route.
  function pathsFor(actor: any): {target: Cell;path: Cell[]}[] {
    if (paths.has(actor.id)) return paths.get(actor.id)!;
    const maximum=Math.floor(Math.max(safeRange(water),safeRange(receive),safeRange(brute),safeRange(evade))*cfg.client_ranges.max_distance_factor);
    const occupied=new Set(world.entities.filter((e: any)=>e.hp>0 && e.id!==actor.id).map((e: any)=>cpuCellKey(e.position)));
    const result=[];
    for (let dq=-maximum;dq<=maximum;dq++) for (let dr=-maximum;dr<=maximum;dr++) {
      const target={q:actor.position.q+dq,r:actor.position.r+dr};
      if (!inBounds(target) || cpuDistance(actor.position,target)>maximum || occupied.has(cpuCellKey(target))) continue;
      const path=[actor.position];let current=actor.position;
      while (cpuDistance(current,target)>0 && path.length<=maximum) {
        const next=directions.map(([q,r])=>({q:current.q+q,r:current.r+r}))
          .find(p=>inBounds(p) && !occupied.has(cpuCellKey(p)) && cpuDistance(p,target)<cpuDistance(current,target));
        if (!next) break;
        path.push(next);current=next;
      }
      if (cpuDistance(current,target)===0) result.push({target,path});
    }
    paths.set(actor.id,result);return result;
  }
  function runs(actor: any,elements: Elements): Run[] {
    const safe=safeRange(elements), maximum=safe*cfg.client_ranges.max_distance_factor;
    // Normal/expert can consider the entire risky range; beginner searches less.
    const budget=Math.min(Math.floor(maximum),levelName==='beginner'?level.search_radius:Math.floor(maximum));
    const rule=cfg.movement.overextension;
    return pathsFor(actor).filter(p=>p.path.length-1<=budget).map(p=>{
      const d=Math.max(...p.path.map(c=>cpuDistance(actor.position,c)));
      const ratio=maximum>safe?Math.max(0,Math.min(1,(d-safe)/(maximum-safe))):0;
      const risk=rule.enabled && d>safe && maximum>safe?rule.fall_probability_at_max*Math.pow(ratio,rule.exponent):0;
      return {actor,target:p.target,elements,path:p.path,speed:speed(actor,elements),risk};
    });
  }
  function position(run: Run,seconds: number): Cell {
    const traveled=Math.max(0,Math.min(run.path.length-1,seconds*run.speed));
    const index=Math.min(run.path.length-1,Math.floor(traveled)),a=run.path[index],b=run.path[Math.min(index+1,run.path.length-1)];
    return {q:a.q+(b.q-a.q)*(traveled-index),r:a.r+(b.r-a.r)*(traveled-index)};
  }
  function stand(actor: any,elements: Elements): Run {return {actor,target:actor.position,path:[actor.position],elements,speed:speed(actor,elements),risk:0};}
  function combatLoss(actor: any,elements: Elements,enemy: any): number {
    const own=actor.stats.strength+elements.TERRE*cfg.actions.element_effects.terre.attack_bonus_per;
    const opposing=enemy.stats.strength+cfg.actions.element_effects.terre.attack_bonus_per;
    const damage=cfg.combat.duel.damage_on_win+1;
    if (own>opposing) return .025;
    if (own===opposing) return actor.hp<=cfg.combat.duel.damage_on_tie+1?.95:.06;
    // FEU/agility can beat an attack through the same dodge thresholds used by
    // the engine. Opposing element allocation is unknown, so use one TERRE.
    if (elements.FEU>1 && actor.stats.agility>=enemy.stats.agility) return .08;
    if (actor.hp<=damage) return .98;
    return Math.min(.99,Math.min(.95,cfg.simulation.fall_base+(opposing-own)*cfg.simulation.fall_per_power)+.08*(1-actor.hp/actor.max_hp));
  }
  function survival(run: Run,fromSeconds=0,toSeconds=Infinity): number {
    let result=1-run.risk;
    for (const enemy of enemies) {
      // Movement resolves before contact on tick zero. An adjacent runner can
      // escape backwards immediately; do not score its old cell as a fight.
      const contact=run.path.some((p,i)=>i/run.speed>=fromSeconds && i/run.speed<=toSeconds &&
        cpuDistance(i===0?position(run,dt):p,enemy.position)<=cfg.combat.trigger_distance_cells+.05);
      if (contact) result*=1-combatLoss(run.actor,run.elements,enemy);
    }
    return result;
  }
  function pressure(actor: any,elements: Elements,p: Cell): number {
    return enemies.reduce((sum: number,e: any)=>sum+Math.max(0,4-cpuDistance(e.position,p))*(.12+combatLoss(actor,elements,e)),0);
  }
  const crowd=(p: Cell)=>[...used.values()].reduce((n,r)=>n+Math.max(0,3-cpuDistance(p,r.target)),0);
  function terminal(run: Run,origin: Cell,fromSeconds=0): number {
    const gain=forward(run.target)-forward(origin), scoring=forward(run.target)>goal;
    const value=36+gain*3.5*personality.progress/20+(scoring?100:0)-pressure(run.actor,run.elements,run.target)*6;
    return survival(run,fromSeconds)*value-36-(run.path.length-1)*.035-run.risk*12*(personality.risk/18-1);
  }
  function select(actor: any,allocations: Elements[],score: (r: Run)=>number): Run {
    let best=stand(actor,allocations[0]), value=-Infinity;
    for (const e of allocations) for (const run of runs(actor,e)) {
      if (reserved.has(cpuCellKey(run.target))) continue;
      const v=score(run);
      if (v>value+1e-8) {best=run;value=v;}
    }
    return best;
  }
  function assign(run: Run,role: string,protect=false): void {
    used.set(run.actor.id,run);reserved.add(cpuCellKey(run.target));roles.push({entity_id:run.actor.id,role,movement_risk:run.risk});
    if (protect) protectedIds.add(run.actor.id);
  }
  const carrier=available.find((e: any)=>e.id===world.ball.holder_entity_id);
  const enemyCarrier=enemies.find((e: any)=>e.id===world.ball.holder_entity_id);
  let strategy='recover',pass: any=null;
  function projectPass(thrower: Run,receiver: Run): any {
    const range=cfg.ball.base_range+thrower.elements.AIR*cfg.actions.element_effects.air.range_modifier;
    const ballStep=cfg.ball.throw_speed_cells_per_sec*dt;
    for (let release=cfg.simulation.throw_delay_ticks;release<cfg.tick_system.max_ticks_per_turn;release++) {
      const origin=position(thrower,(release+1)*dt);
      if (forward(origin)>goal && forward(cpuRound(origin))>goal) return null;
      let landing: Cell|undefined, duration=0;
      const latest=Math.ceil((cpuDistance(origin,receiver.actor.position)+receiver.path.length+1)/ballStep);
      for (let ticks=1;ticks<=latest;ticks++) {
        const target=cpuRound(position(receiver,(release+ticks+1)*dt));
        if (cpuDistance(origin,target)<=ballStep*ticks) {landing=target;duration=ticks;break;}
      }
      if (!landing || cpuDistance(origin,landing)>range) continue;
      if (release+duration>=cfg.tick_system.max_ticks_per_turn) return null;
      const d=cpuDistance(origin,landing);
      const accuracy=probability(cfg.simulation.throw_base+thrower.actor.stats.precision*cfg.simulation.throw_stat+
        thrower.elements.AIR*cfg.probabilities.air_precision_per_action-d*cfg.simulation.distance_penalty);
      let windows=0, laneSurvival=1;
      const lowSamples: {p: Cell;time: number}[]=[];
      for (let t=1;t<=duration;t++) {
        const height=4*cfg.ball.arc_height_cells*t*(duration-t)/(duration*duration);
        if (height>cfg.ball.intercept_height_threshold) continue;
        const p={q:origin.q+(landing.q-origin.q)*t/duration,r:origin.r+(landing.r-origin.r)*t/duration};
        const time=(release+t+1)*dt;
        lowSamples.push({p,time});
        if (cpuDistance(position(receiver,time),p)<=cfg.ball.catch_radius_cells) windows++;
      }
      for (const enemy of enemies) {
        let threat=0;
        for (const {p,time} of lowSamples) {
          const distance=cpuDistance(enemy.position,p),reach=Math.min(safeRange(intercept),speed(enemy,intercept)*time);
          if (distance>reach+cfg.ball.intercept_radius_cells) continue;
          const confidence=distance<=cfg.ball.intercept_radius_cells?1:.35*Math.max(0,1-(distance-cfg.ball.intercept_radius_cells)/(reach+.01));
          threat=Math.max(threat,confidence*probability(cfg.simulation.catch_base+enemy.stats.precision*cfg.simulation.catch_stat+cfg.simulation.catch_feu));
        }
        laneSurvival*=1-threat;
      }
      const catchChance=probability(cfg.simulation.catch_base+receiver.actor.stats.precision*cfg.simulation.catch_stat+receiver.elements.AIR*cfg.simulation.catch_air);
      const catches=1-Math.pow(1-catchChance,Math.min(receiver.elements.AIR,windows));
      const arrival=(release+duration+1)*dt;
      const chance=accuracy*catches*laneSurvival*survival(thrower,0,(release+1)*dt);
      return {release_tick:release,land_tick:release+duration,landing,chance,arrival};
    }
    return null;
  }
  if (carrier) {
    strategy='carry';
    const carry=select(carrier,[water,brute,evade],r=>terminal(r,carrier.position));
    let chosen=carry,best=terminal(carry,carrier.position),chosenReceiver: Run|null=null;
    if (level.passes && slots>0) {
      const launches=[receive,accurate].flatMap(e=>{
        const candidates=runs(carrier,e).sort((a,b)=>terminal(b,carrier.position)-terminal(a,carrier.position));
        return [stand(carrier,e),...candidates.slice(0,3)];
      });
      for (const receiver of available.filter((e: any)=>e.id!==carrier.id)) {
        const receptionRuns=[receive,accurate].flatMap(e=>runs(receiver,e)
          .sort((a,b)=>terminal(b,carrier.position)-terminal(a,carrier.position)).slice(0,4));
        // Short support runs and switches across the pitch can be preferable to
        // sending every potential receiver to its furthest forward cell.
        for (const e of [receive,accurate]) for (const gain of [0,3,6]) {
          const anchor=at(cpuColumn(receiver.position)+direction*gain,receiver.position.r);
          receptionRuns.push(select(receiver,[e],r=>-cpuDistance(r.target,anchor)*4-r.risk*35-
            pressure(receiver,e,r.target)*4));
        }
        receptionRuns.push(stand(receiver,allocation(['AIR','AIR','AIR'])));
        const towardsReceiver=[receive,accurate].map(e=>select(carrier,[e],r=>
          -cpuDistance(r.target,receiver.position)*3-pressure(carrier,e,r.target)*6-r.risk*40));
        for (const r of receptionRuns) for (const launch of [...launches,...towardsReceiver]) {
          if (cpuDistance(launch.target,r.target)<1) continue;
          const flight=projectPass(launch,r);
          if (!flight) continue;
          const value=flight.chance*(terminal(r,carrier.position,flight.arrival)+36)-36-1.5+
            Math.max(0,personality.passing-24)*.08;
          if (value>best+.5) {best=value;chosen=launch;chosenReceiver=r;pass={...flight,thrower:carrier.id,receiver:receiver.id};}
        }
      }
    }
    assign(chosen,'carrier',true);
    if (chosenReceiver) {assign(chosenReceiver,'receiver',true);strategy='pass';}
    else if (forward(chosen.target)<forward(carrier.position)-.5) strategy='retreat';
    else if (chosen.elements.TERRE>0) strategy='breakthrough';
    const focus=chosenReceiver?.target ?? chosen.target;
    // Distinct support lanes: one screen, two wide runners, and cover behind.
    const support=available.filter((e: any)=>!used.has(e.id));
    const screen=[...support].sort((a: any,b: any)=>(b.stats.strength+b.hp*.25-cpuDistance(b.position,focus))-(a.stats.strength+a.hp*.25-cpuDistance(a.position,focus)) || a.id-b.id)[0];
    if (screen) {
      const anchor=at(cpuColumn(focus)+direction*1.5,focus.r+(focus.r>0?-2:2));
      assign(select(screen,[brute],r=>-cpuDistance(r.target,anchor)*3-r.risk*30-crowd(r.target)*5),'screen');
    }
    const rest=support.filter((e: any)=>e.id!==screen?.id).sort((a: any,b: any)=>b.stats.precision+b.stats.endurance-a.stats.precision-a.stats.endurance || a.id-b.id);
    for (const [i,actor] of rest.entries()) {
      const cover=i===rest.length-1 && rest.length>1;
      const row=cover?focus.r/2:Math.max(-8,Math.min(8,focus.r+(i%2===0?-4:4)));
      const anchor=at(cpuColumn(focus)+direction*(cover?-5:1),row);
      assign(select(actor,[cover?runner:receive],r=>-cpuDistance(r.target,anchor)*3-r.risk*30-
        pressure(actor,r.elements,r.target)*2-crowd(r.target)*6),cover?'cover':'parallel_support');
    }
  } else if (enemyCarrier) {
    strategy='defend';
    const press=[...available].sort((a: any,b: any)=>{
      const suitability=(e: any)=>e.stats.strength*.9+e.stats.agility*.1+e.hp*.2-e.stats.precision*.25-
        cpuDistance(e.position,enemyCarrier.position)*1.4;
      return suitability(b)-suitability(a) || a.id-b.id;
    })[0];
    if (press) {
      const enemyGoal=-direction*goal;
      const anchor=at(cpuColumn(enemyCarrier.position)-direction*2,enemyCarrier.position.r);
      assign(select(press,[allocation(['TERRE','TERRE','FEU']),allocation(['TERRE','FEU','EAU']),evade],r=>-cpuDistance(r.target,anchor)*3+
        (cpuDistance(r.target,enemyCarrier.position)<=1?10*(1-combatLoss(press,r.elements,enemyCarrier)):0)-r.risk*24-
        (Math.abs(cpuColumn(enemyCarrier.position)-enemyGoal)<4?r.risk*-15:0)),'pressure',true);
    }
    // Guess valuable enemy passes from visible progress, receiver precision and
    // space, then cover reachable low parts of those flight paths before arrival.
    const options: any[]=[];
    for (const receiver of enemies.filter((e: any)=>e.id!==enemyCarrier.id)) {
      const gain=-direction*(cpuColumn(receiver.position)-cpuColumn(enemyCarrier.position));
      const d=cpuDistance(enemyCarrier.position,receiver.position);
      if (d>cfg.ball.base_range+2*cfg.actions.element_effects.air.range_modifier || d<2) continue;
      const value=6+Math.max(0,gain)*2+receiver.stats.precision*.25;
      const ticks=Math.max(1,Math.ceil(d/(cfg.ball.throw_speed_cells_per_sec*dt)));
      for (let t=1;t<=ticks;t++) {
        const height=4*cfg.ball.arc_height_cells*t*(ticks-t)/(ticks*ticks);
        if (height>cfg.ball.intercept_height_threshold) continue;
        const p={q:enemyCarrier.position.q+(receiver.position.q-enemyCarrier.position.q)*t/ticks,
          r:enemyCarrier.position.r+(receiver.position.r-enemyCarrier.position.r)*t/ticks};
        options.push({p,time:(cfg.simulation.throw_delay_ticks+t+1)*dt,value,receiver:receiver.id});
      }
    }
    const remaining=available.filter((e: any)=>!used.has(e.id));
    while (options.length && remaining.length>1) {
      let best: any=null;
      for (const actor of remaining) for (const run of runs(actor,intercept)) {
        if (reserved.has(cpuCellKey(run.target))) continue;
        for (const option of options) {
          const d=cpuDistance(position(run,option.time),option.p);
          if (d>cfg.ball.intercept_radius_cells) continue;
          const catchChance=probability(cfg.simulation.catch_base+actor.stats.precision*cfg.simulation.catch_stat+intercept.FEU*cfg.simulation.catch_feu);
          const score=option.value*catchChance-cpuDistance(run.target,option.p)*2-run.risk*25-crowd(run.target)*5;
          if (!best || score>best.score) best={actor,run,option,score};
        }
      }
      if (!best || best.score<3) break;
      assign(best.run,'pass_interceptor',true);
      remaining.splice(remaining.indexOf(best.actor),1);
      for (let i=options.length-1;i>=0;i--) if (options[i].receiver===best.option.receiver) options.splice(i,1);
    }
    for (const [i,actor] of remaining.entries()) {
      const anchor=at(cpuColumn(enemyCarrier.position)-direction*(4+i*2),i%2===0?-3:3);
      assign(select(actor,[runner,intercept],r=>-cpuDistance(r.target,anchor)*3-r.risk*28-crowd(r.target)*6),'cover');
    }
  } else if (available.length) {
    // Pick the retriever by arrival time, pickup skill, health and fall risk,
    // rather than simply assigning the lowest ID to the ball.
    let collection: any=null;
    for (const actor of available) for (const e of [runner,evade,receive]) for (const run of runs(actor,e)) {
      const gap=cpuDistance(run.target,world.ball.position);
      const attempts=e.FEU+e.AIR;
      const chance=1-Math.pow(1-probability(cfg.simulation.catch_base+actor.stats.precision*cfg.simulation.catch_stat+
        e.AIR*cfg.simulation.catch_air+e.FEU*cfg.simulation.catch_feu),attempts);
      const value=(gap<=cfg.ball.pickup_range?40*chance:0)-gap*4-(run.path.length-1)/run.speed*2-
        run.risk*32-pressure(actor,e,run.target)*3;
      if (!collection || value>collection.value) collection={run,value};
    }
    if (collection) assign(collection.run,'retriever',true);
    const focus=world.ball.position,rest=available.filter((e: any)=>!used.has(e.id))
      .sort((a: any,b: any)=>b.stats.precision+b.stats.endurance-a.stats.precision-a.stats.endurance || a.id-b.id);
    for (const [i,actor] of rest.entries()) {
      const cover=i===rest.length-1 && rest.length>1;
      const anchor=at(cpuColumn(focus)+direction*(cover?-5:i===0?5:3),cover?0:i%2===0?-3:4);
      // One player collects; accurate, fast teammates get ahead now so a pass
      // is available next turn. They need no pickup actions on this support run.
      assign(select(actor,i===0?[water,receive]:[receive],r=>-cpuDistance(r.target,anchor)*3-r.risk*28-crowd(r.target)*6-
        pressure(actor,r.elements,r.target)*2-(r.elements.AIR+r.elements.FEU===0 &&
          r.path.some(p=>cpuDistance(p,focus)<=cfg.ball.pickup_range)?25:0)),cover?'cover':i===0?'forward_outlet':'recovery_support');
    }
  }
  const actions: any[]=[];
  for (const actor of team) {
    const run=used.get(actor.id);
    if (!run) {actions.push({entity_id:actor.id,action_type:'wait',params:{elements:{...water}}});continue;}
    const moving=cpuDistance(actor.position,run.target)>0;
    actions.push({entity_id:actor.id,action_type:moving?'move':'wait',params:{elements:{...run.elements},...(moving?{target_position:run.target}:{})}});
    if (pass?.thrower===actor.id) actions.push({entity_id:actor.id,action_type:'throw',params:{elements:{...run.elements},target_entity_id:pass.receiver}});
  }
  return {...order,actions,cpu_plan:{version:2,strategy,roles,protected_ids:[...protectedIds],
    ...(pass?{pass:{thrower:pass.thrower,receiver:pass.receiver,release_tick:pass.release_tick,land_tick:pass.land_tick,
      landing:pass.landing,estimated_success:pass.chance}}:{})}};
}
