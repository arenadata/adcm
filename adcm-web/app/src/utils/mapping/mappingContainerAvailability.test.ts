import { AdcmHostComponentMapRuleAction } from '@models/adcm';
import { buildComponentHostRelations, HOST_MM, SERVICE_NOT_CREATED } from './componentHostRelations';
import {
  buildComponentContainerAvailabilityFromRelations,
  buildHostContainerAvailabilityFromRelations,
} from './mappingContainerAvailability';
import { hbaseMaster, hostAlpha, hostGamma, hosts, zkServer } from './__fixtures__/mappingFixtures';

describe('mappingContainerAvailability', () => {
  test('installed service denies Add and unmap delete', () => {
    const relations = buildComponentHostRelations({
      hosts,
      components: [hbaseMaster],
      baselinePairs: [{ hostId: hostAlpha.id, componentId: hbaseMaster.id }],
      policy: { type: 'cluster' },
    });
    const availability = buildComponentContainerAvailabilityFromRelations(
      relations,
      hbaseMaster.id,
      hosts,
      new Set([hostAlpha.id]),
    );
    expect(availability.notAvailableError).toBe(SERVICE_NOT_CREATED);
    expect(availability.addError).toBe(SERVICE_NOT_CREATED);
    expect(availability.mappedHostDelete[hostAlpha.id]).toEqual({
      disabled: true,
      title: SERVICE_NOT_CREATED,
    });
    expect(availability.hostOptions[hostAlpha.id].disabled).toBe(true);
  });

  test('MM empty host blocks Add; mapped count > 0 does not', () => {
    const relationsEmpty = buildComponentHostRelations({
      hosts: [hostGamma],
      components: [zkServer],
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    const emptyHost = buildHostContainerAvailabilityFromRelations(relationsEmpty, hostGamma.id, [zkServer], new Set());
    expect(emptyHost.addError).toBe(HOST_MM);

    const relationsBaseline = buildComponentHostRelations({
      hosts: [hostGamma],
      components: [zkServer],
      baselinePairs: [{ hostId: hostGamma.id, componentId: zkServer.id }],
      policy: { type: 'cluster' },
    });
    const withMapped = buildHostContainerAvailabilityFromRelations(
      relationsBaseline,
      hostGamma.id,
      [zkServer],
      new Set([zkServer.id]),
    );
    expect(withMapped.addError).toBeUndefined();
  });

  test('Add-only: baseline host option disabled for unmap', () => {
    const relations = buildComponentHostRelations({
      hosts: [hostAlpha],
      components: [zkServer],
      baselinePairs: [{ hostId: hostAlpha.id, componentId: zkServer.id }],
      policy: {
        type: 'actionRules',
        rules: [{ service: 'zookeeper', component: 'zk_server', operation: AdcmHostComponentMapRuleAction.Add }],
      },
    });
    const availability = buildComponentContainerAvailabilityFromRelations(
      relations,
      zkServer.id,
      [hostAlpha],
      new Set([hostAlpha.id]),
    );
    expect(availability.hostOptions[hostAlpha.id].disabled).toBe(true);
    expect(availability.mappedHostDelete[hostAlpha.id].disabled).toBe(true);
  });
});
