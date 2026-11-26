import { AdcmHostComponentMapRuleAction } from '@models/adcm';
import {
  ADD_NOT_ALLOWED,
  buildComponentHostRelations,
  getComponentLevelMapDeny,
  getHostMapBlockedReason,
  getPairRelation,
  HOST_MM,
  isPairMapAllowed,
  isPairUnmapAllowed,
  makePairKey,
  MAPPING_NOT_ALLOWED,
  REMOVE_NOT_ALLOWED,
  SERVICE_NOT_CREATED,
} from './componentHostRelations';
import {
  components,
  hbaseMaster,
  hostAlpha,
  hostBeta,
  hostGamma,
  hosts,
  zkServer,
} from './__fixtures__/mappingFixtures';

describe('buildComponentHostRelations', () => {
  test('creates one entry per component x host', () => {
    const relations = buildComponentHostRelations({
      hosts,
      components,
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    expect(relations.pairs.size).toBe(hosts.length * components.length);
    const key = makePairKey(zkServer.id, hostAlpha.id);
    expect(relations.pairs.get(key)).toEqual({ map: { denyReasons: [] }, unmap: { denyReasons: [] } });
  });

  test('cluster: installed service denies map and unmap on all hosts', () => {
    const relations = buildComponentHostRelations({
      hosts,
      components: [hbaseMaster],
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    const rel = getPairRelation(relations, hbaseMaster.id, hostAlpha.id);
    expect(rel.map.denyReasons).toContain(SERVICE_NOT_CREATED);
    expect(rel.unmap.denyReasons).toContain(SERVICE_NOT_CREATED);
    expect(getComponentLevelMapDeny(relations, hbaseMaster.id)).toBe(SERVICE_NOT_CREATED);
    expect(isPairMapAllowed(rel)).toBe(false);
    expect(isPairUnmapAllowed(rel)).toBe(false);
  });

  test('cluster: MM host denies map unless baseline-mapped', () => {
    const relationsEmpty = buildComponentHostRelations({
      hosts: [hostGamma],
      components: [zkServer],
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    expect(getPairRelation(relationsEmpty, zkServer.id, hostGamma.id).map.denyReasons).toContain(HOST_MM);
    expect(getHostMapBlockedReason(relationsEmpty, hostGamma.id, [zkServer.id], 0)).toBe(HOST_MM);

    const relationsBaseline = buildComponentHostRelations({
      hosts: [hostGamma],
      components: [zkServer],
      baselinePairs: [{ hostId: hostGamma.id, componentId: zkServer.id }],
      policy: { type: 'cluster' },
    });
    expect(getPairRelation(relationsBaseline, zkServer.id, hostGamma.id).map.denyReasons).not.toContain(HOST_MM);
    expect(getHostMapBlockedReason(relationsBaseline, hostGamma.id, [zkServer.id], 0)).toBeUndefined();
    expect(getHostMapBlockedReason(relationsEmpty, hostGamma.id, [zkServer.id], 1)).toBeUndefined();
  });

  test('actionRules Add-only: baseline host cannot unmap', () => {
    const addOnly = {
      type: 'actionRules' as const,
      rules: [{ service: 'zookeeper', component: 'zk_server', operation: AdcmHostComponentMapRuleAction.Add }],
    };
    const relations = buildComponentHostRelations({
      hosts: [hostAlpha, hostBeta],
      components: [zkServer],
      baselinePairs: [{ hostId: hostAlpha.id, componentId: zkServer.id }],
      policy: addOnly,
    });
    expect(getPairRelation(relations, zkServer.id, hostAlpha.id).unmap.denyReasons).toContain(REMOVE_NOT_ALLOWED);
    expect(getPairRelation(relations, zkServer.id, hostBeta.id).unmap.denyReasons).toEqual([]);
    expect(getPairRelation(relations, zkServer.id, hostBeta.id).map.denyReasons).toEqual([]);
  });

  test('actionRules: no rules denies map and unmap', () => {
    const relations = buildComponentHostRelations({
      hosts: [hostAlpha],
      components: [zkServer],
      baselinePairs: [],
      policy: { type: 'actionRules', rules: [] },
    });
    const rel = getPairRelation(relations, zkServer.id, hostAlpha.id);
    expect(rel.map.denyReasons).toEqual([MAPPING_NOT_ALLOWED]);
    expect(rel.unmap.denyReasons).toEqual([MAPPING_NOT_ALLOWED]);
  });

  test('actionRules: MM host with Add still denied when not baseline', () => {
    const addOnly = {
      type: 'actionRules' as const,
      rules: [{ service: 'zookeeper', component: 'zk_server', operation: AdcmHostComponentMapRuleAction.Add }],
    };
    const relations = buildComponentHostRelations({
      hosts: [hostGamma],
      components: [zkServer],
      baselinePairs: [],
      policy: addOnly,
    });
    expect(getPairRelation(relations, zkServer.id, hostGamma.id).map.denyReasons).toContain(HOST_MM);
  });

  test('actionRules: without Add denies map for non-baseline host', () => {
    const removeOnly = {
      type: 'actionRules' as const,
      rules: [{ service: 'zookeeper', component: 'zk_server', operation: AdcmHostComponentMapRuleAction.Remove }],
    };
    const relations = buildComponentHostRelations({
      hosts: [hostAlpha],
      components: [zkServer],
      baselinePairs: [],
      policy: removeOnly,
    });
    expect(getPairRelation(relations, zkServer.id, hostAlpha.id).map.denyReasons).toContain(ADD_NOT_ALLOWED);
  });

  test('componentLevelDeny distinguishes ids 1 and 10', () => {
    const component1 = { ...hbaseMaster, id: 1 };
    const component10 = { ...zkServer, id: 10 };
    const relations = buildComponentHostRelations({
      hosts: [hostAlpha],
      components: [component1, component10],
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    expect(getComponentLevelMapDeny(relations, 1)).toBe(SERVICE_NOT_CREATED);
    expect(getComponentLevelMapDeny(relations, 10)).toBeUndefined();
    expect(getPairRelation(relations, 10, hostAlpha.id).map.denyReasons).toEqual([]);
  });

  test('componentLevelDeny works with empty hosts', () => {
    const relations = buildComponentHostRelations({
      hosts: [],
      components: [hbaseMaster, zkServer],
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    expect(relations.pairs.size).toBe(0);
    expect(getComponentLevelMapDeny(relations, hbaseMaster.id)).toBe(SERVICE_NOT_CREATED);
    expect(getComponentLevelMapDeny(relations, zkServer.id)).toBeUndefined();
  });

  test('componentLevelDeny ignores host order', () => {
    const relations = buildComponentHostRelations({
      hosts: [hostBeta, hostAlpha],
      components: [hbaseMaster],
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    expect(getComponentLevelMapDeny(relations, hbaseMaster.id)).toBe(SERVICE_NOT_CREATED);
  });

  test('getPairRelation throws when pair is missing', () => {
    const relations = buildComponentHostRelations({
      hosts: [hostAlpha],
      components: [zkServer],
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    expect(() => getPairRelation(relations, zkServer.id, hostBeta.id)).toThrow(/Missing ComponentHostRelations/);
  });
});
