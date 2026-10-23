import {describe,test,expect} from "bun:test";
import {rulebookConsequences,applyRulebookDamage,recordRulebookLoss,rulebookPickupPenalty} from "../backend/simulator/rulebook";
import {rulebookOverlay} from "../backend/simulator/overlays";

describe("Documented consequences, independent of the unknown score formula", () => {
  for (const branch of ["targeted","incidental","dodge"]) for (const [index,tier] of ["normal","wide","critical"].entries()) {
    test(`${branch} ${tier}`, () => {
      const effect=rulebookConsequences(tier,branch);
      expect(effect.damage).toBe((branch==="targeted"?[1,3,5]:[0,2,4])[index]);
      expect(effect.down).toBe(branch==="targeted" && index>0);
      expect(effect.stun).toBe(!effect.down);
    });
  }
  test("Disputed critical dodge is isolated from incidental four-damage hits", () => {
    expect(rulebookConsequences("critical","dodge",true).down).toBe(true);
    expect(rulebookConsequences("critical","incidental",true).down).toBe(false);
    expect(()=>rulebookConsequences("invented","dodge")).toThrow();
  });
  test("Shield then temporary HP then permanent HP; no resurrection", () => {
    const actor={shield_hp:2,temporary_hp:3,hp:4};
    expect(applyRulebookDamage(actor,7)).toEqual({damage:2,absorbed_shield:2,absorbed_temporary:3,hp:2});
    expect(applyRulebookDamage(actor,20).hp).toBe(0);
    expect(applyRulebookDamage(actor,0).hp).toBe(0);
  });
  test("Lost combats reset by world/turn identity, not a persistent player field", () => {
    const actor={id:1,hp:5,position:{q:0,r:0}},state={entities:[actor]};
    const cfg={rulebook:{pickup:{radius:1,nearby_penalty:.1,loss_penalty:.1}}};
    recordRulebookLoss(state,1);recordRulebookLoss(state,1);
    expect(rulebookPickupPenalty(cfg,state,actor).lost_combats).toBe(2);
    expect(rulebookPickupPenalty(cfg,structuredClone(state),actor).lost_combats).toBe(0);
  });
});

test("Archive overlays fail closed and add turn hooks once", () => {
  const source='import {sample} from "x";\nfor (let tick = 0; tick < cfg.tick_system.max_ticks_per_turn; tick++) {}\nconst final_entity_states = [];';
  const patched=rulebookOverlay("engine",source);
  expect(patched).toContain('prepareRulebookTurn(cfg, state);');
  expect(rulebookOverlay("engine",patched)).toBe(patched);
  expect(()=>rulebookOverlay("engine","unrecognized engine")).toThrow();
  expect(()=>rulebookOverlay("turnTick","unrecognized ticks")).toThrow();
});
