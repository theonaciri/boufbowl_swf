// Explanatory calculations use the configuration embedded by the website build.
export function ruleCalculator(config) {
  const {simulation:c,client_ranges:r}=config, s=c.simulation, p=c.rulebook;
  const bounded=x=>Math.max(s.probability_min,Math.min(s.probability_max,x));
  return {
    range:orders=>(c.ball.base_range+orders*c.actions.element_effects.air.range_modifier)*(c.ball.range_multiplier??1),
    throwFailure(stat,orders,distance){
      if(orders<1) return 100;
      if(distance>this.range(orders)) return c.ball.attempt_out_of_range ? 100 : null;
      return 100*(1-bounded(s.throw_base+stat*s.throw_stat+orders*c.probabilities.air_precision_per_action-distance*s.distance_penalty));
    },
    catchFailure:(stat,orders,interception=false)=>orders<1?100:100*(1-bounded(s.catch_base+stat*s.catch_stat+orders*(interception?s.catch_feu:s.catch_air))),
    pickupFailure:(stat,air,fire,nearby,losses)=>air+fire<1?100:100*(1-bounded(s.catch_base+stat*s.catch_stat+air*s.catch_air+fire*s.catch_feu-nearby*p.pickup.nearby_penalty-losses*p.pickup.loss_penalty)),
    movement(stat,orders,distance){
      const safe=orders.reduce((sum,n,i)=>sum+n*r[['earth_distance_bonus','fire_distance_bonus','air_distance_bonus','water_distance_bonus'][i]],0);
      const maximum=safe*r.max_distance_factor;
      if(distance===0) return {safe,maximum,failure:0};
      if(distance>maximum) return {safe,maximum,failure:null};
      const ratio=maximum>safe?Math.max(0,Math.min(1,(distance-safe)/(maximum-safe))):0;
      const extension=c.movement.overextension.enabled?c.movement.overextension.fall_probability_at_max*ratio**c.movement.overextension.exponent:0;
      return {safe,maximum,failure:c.movement.overextension.enabled?100*Math.min(1,(p.movement.safe_failure+extension)/(1+stat*p.movement.water_stat+orders[3]*p.movement.water_order)):0};
    },
    stun:water=>Math.max(p.status.minimum_ticks,Math.ceil(p.status.base_ticks-Math.max(0,water)*p.status.water_reduction))*c.tick_system.tick_dt_seconds,
    combat:margin=>p.combat.random_score ? 100/(1+Math.exp(-margin/p.combat.random_score.scale)) : null,
  };
}
