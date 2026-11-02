import { AdcmHostComponentMapRuleAction } from '@models/adcm';
import { buildMappingModel } from './buildMappingModel';
import { buildComponentHostRelations } from './componentHostRelations';
import { computeMappingAvailability } from './mappingAvailability';
import { getRulesForComponent } from './mappingRules';
import {
  components,
  hbaseMaster,
  hostAlpha,
  hostGamma,
  hosts,
  zkClient,
  zkServer,
} from './__fixtures__/mappingFixtures';

describe('computeMappingAvailability', () => {
  const model = buildMappingModel([], hosts, components);

  test('cluster: installed service not available; zk editable', () => {
    const relations = buildComponentHostRelations({
      hosts,
      components,
      baselinePairs: [],
      policy: { type: 'cluster' },
    });
    const availability = computeMappingAvailability(model, relations);
    expect(availability.components[hbaseMaster.id].notAvailableReason).toBeDefined();
    expect(availability.components[hbaseMaster.id].canMap).toBe(false);
    expect(availability.components[hbaseMaster.id].canUnmap).toBe(false);
    expect(availability.components[zkServer.id].notAvailableReason).toBeUndefined();
    expect(availability.components[zkServer.id].canMap).toBe(true);
    expect(availability.services[zkServer.service.id].isEditable).toBe(true);
    expect(availability.services[hbaseMaster.service.id].isEditable).toBe(false);
  });

  test('actionRules: MM host cannot map; alpha can', () => {
    const relations = buildComponentHostRelations({
      hosts,
      components,
      baselinePairs: [],
      policy: {
        type: 'actionRules',
        rules: [
          {
            service: 'zookeeper',
            component: 'zk_server',
            operation: AdcmHostComponentMapRuleAction.Add,
          },
        ],
      },
    });
    const availability = computeMappingAvailability(model, relations);
    expect(availability.hosts[hostAlpha.id].canMap).toBe(true);
    expect(availability.hosts[hostGamma.id].canMap).toBe(false);
    expect(availability.services[zkServer.service.id].isEditable).toBe(true);
  });

  test('getRulesForComponent matches names', () => {
    const rules = [
      {
        service: 'zookeeper',
        component: 'zk_server',
        operation: AdcmHostComponentMapRuleAction.Add,
      },
    ];
    expect(getRulesForComponent(rules, zkServer).has(AdcmHostComponentMapRuleAction.Add)).toBe(true);
    expect(getRulesForComponent(rules, zkClient).size).toBe(0);
  });
});
