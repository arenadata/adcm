import { AdcmHostComponentMapRuleAction } from '@models/adcm';
import { buildMappingModel } from './buildMappingModel';
import { buildComponentHostRelations } from './componentHostRelations';
import { computeMappingAvailability } from './mappingAvailability';
import { layoutMappingViewModel } from './mappingLayout';
import { components, hosts, pairsAlphaZkServer, zkServer } from './__fixtures__/mappingFixtures';

describe('layoutMappingViewModel', () => {
  const model = buildMappingModel([], hosts, components);
  const clusterRelations = buildComponentHostRelations({
    hosts,
    components,
    baselinePairs: [],
    policy: { type: 'cluster' },
  });
  const clusterAvailability = computeMappingAvailability(model, clusterRelations);

  const zkAddOnlyRelations = buildComponentHostRelations({
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
  const zkAddOnlyAvailability = computeMappingAvailability(model, zkAddOnlyRelations);

  test('services name A-Z: HBase then Zookeeper', () => {
    const view = layoutMappingViewModel(model, clusterAvailability, { kind: 'services', sort: 'name' });
    expect(view.kind).toBe('services');
    if (view.kind === 'services') {
      expect(view.services.map((s) => s.service.name)).toEqual(['hbase', 'zookeeper']);
    }
  });

  test('wizard editableFirst: zookeeper before hbase', () => {
    const view = layoutMappingViewModel(model, zkAddOnlyAvailability, { kind: 'services', sort: 'editableFirst' });
    if (view.kind === 'services') {
      expect(view.services[0].service.name).toBe('zookeeper');
      expect(view.services[0].isEditable).toBe(true);
      expect(view.services[1].isEditable).toBe(false);
    }
  });

  test('flat editableFirst: zk_server first', () => {
    const view = layoutMappingViewModel(model, zkAddOnlyAvailability, { kind: 'flat', sort: 'editableFirst' });
    if (view.kind === 'flat') {
      expect(view.components[0].component.name).toBe('zk_server');
    }
  });

  test('desc reverses editableFirst services order', () => {
    const asc = layoutMappingViewModel(model, zkAddOnlyAvailability, {
      kind: 'services',
      sort: 'editableFirst',
      sortDirection: 'asc',
    });
    const desc = layoutMappingViewModel(model, zkAddOnlyAvailability, {
      kind: 'services',
      sort: 'editableFirst',
      sortDirection: 'desc',
    });
    if (asc.kind === 'services' && desc.kind === 'services') {
      expect(asc.services.map((s) => s.service.name)).toEqual(['zookeeper', 'hbase']);
      expect(desc.services.map((s) => s.service.name)).toEqual(['hbase', 'zookeeper']);
    }
  });

  test('hosts keep mapped component object identity from the model', () => {
    const mappedModel = buildMappingModel(pairsAlphaZkServer, hosts, components);
    const relations = buildComponentHostRelations({
      hosts,
      components,
      baselinePairs: pairsAlphaZkServer,
      policy: { type: 'cluster' },
    });
    const availability = computeMappingAvailability(mappedModel, relations);
    const view = layoutMappingViewModel(mappedModel, availability, { kind: 'hosts', sort: 'name' });

    expect(view.kind).toBe('hosts');
    if (view.kind !== 'hosts') {
      return;
    }

    const alphaFromModel = mappedModel.hostsMapping.find((hostMapping) => hostMapping.host.name === 'alpha');
    const alpha = view.hosts.find((hostMapping) => hostMapping.host.name === 'alpha');
    expect(alpha?.components).toHaveLength(1);
    expect(alpha?.components[0]).toBe(zkServer);
    expect(alpha?.components[0]).toBe(alphaFromModel?.components[0]);
  });
});
