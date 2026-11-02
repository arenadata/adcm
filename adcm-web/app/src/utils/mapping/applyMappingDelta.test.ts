import { applyMappingDelta } from './applyMappingDelta';
import { diffMapping } from './diffMapping';
import { hostAlpha, hostBeta, pairsAlphaZkServer, zkServer } from './__fixtures__/mappingFixtures';

describe('applyMappingDelta', () => {
  test('null delta returns the same mapping array', () => {
    expect(applyMappingDelta(pairsAlphaZkServer, null)).toBe(pairsAlphaZkServer);
  });

  test('add appends a pair with a new id and ignores duplicates', () => {
    const current = [{ id: 7, hostId: hostAlpha.id, componentId: zkServer.id }];
    const once = applyMappingDelta(current, {
      add: [{ hostId: hostBeta.id, componentId: zkServer.id }],
      remove: [],
    });

    expect(once).toEqual([
      { id: 7, hostId: hostAlpha.id, componentId: zkServer.id },
      { id: 8, hostId: hostBeta.id, componentId: zkServer.id },
    ]);

    const duplicate = applyMappingDelta(once, {
      add: [{ hostId: hostBeta.id, componentId: zkServer.id }],
      remove: [],
    });
    expect(duplicate).toEqual(once);
  });

  test('remove deletes by hostId-componentId then add can recreate the pair', () => {
    const current = [{ id: 1, hostId: hostAlpha.id, componentId: zkServer.id }];
    const removed = applyMappingDelta(current, {
      add: [],
      remove: [{ hostId: hostAlpha.id, componentId: zkServer.id }],
    });
    expect(removed).toEqual([]);

    const restored = applyMappingDelta(removed, {
      add: [{ hostId: hostAlpha.id, componentId: zkServer.id }],
      remove: [],
    });
    expect(restored).toEqual([{ id: 1, hostId: hostAlpha.id, componentId: zkServer.id }]);
  });
});

describe('diffMapping', () => {
  test('returns add and remove relative to baseline', () => {
    const baseline = [{ hostId: hostAlpha.id, componentId: zkServer.id }];
    const local = [{ hostId: hostBeta.id, componentId: zkServer.id }];
    expect(diffMapping(baseline, local)).toEqual({
      add: [{ hostId: hostBeta.id, componentId: zkServer.id }],
      remove: [{ hostId: hostAlpha.id, componentId: zkServer.id }],
    });
  });
});
