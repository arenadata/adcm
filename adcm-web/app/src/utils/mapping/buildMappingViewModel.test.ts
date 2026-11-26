import { AdcmHostComponentMapRuleAction } from '@models/adcm';
import { buildMappingCore } from './buildMappingViewModel';
import { buildComponentHostRelations } from './componentHostRelations';
import { layoutMappingViewModel } from './mappingLayout';
import { components, hostAlpha, hostBeta, hosts, pairsAlphaZkServer, zkServer } from './__fixtures__/mappingFixtures';
import type { MappingViewConfig } from './mapping.types';

const relationsFor = (viewConfig: MappingViewConfig, baselinePairs = pairsAlphaZkServer) =>
  buildComponentHostRelations({
    hosts,
    components,
    baselinePairs,
    policy: viewConfig.strategy,
  });

const buildView = (pairs: typeof pairsAlphaZkServer, viewConfig: MappingViewConfig, baselinePairs = pairs) => {
  const relations = relationsFor(viewConfig, baselinePairs);
  const core = buildMappingCore(pairs, hosts, components, {}, relations);
  const viewModel = layoutMappingViewModel(core.model, core.availability, {
    kind: viewConfig.kind,
    sort: viewConfig.sort,
    sortDirection: viewConfig.sortDirection,
  });
  return { ...core, viewModel };
};

describe('buildMappingCore + layout', () => {
  test('cluster page view-model: grouped, name sort', () => {
    const viewConfig: MappingViewConfig = {
      strategy: { type: 'cluster' },
      kind: 'services',
      sort: 'name',
    };
    const { viewModel, relations } = buildView(pairsAlphaZkServer, viewConfig);
    expect(viewModel.kind).toBe('services');
    expect(relations.pairs.size).toBe(hosts.length * components.length);
  });

  test('relations baseline ignores local pairs for Add-only unmap', () => {
    const localPairs = [...pairsAlphaZkServer, { hostId: hostBeta.id, componentId: zkServer.id }];
    const viewConfig: MappingViewConfig = {
      strategy: {
        type: 'actionRules',
        rules: [
          {
            service: 'zookeeper',
            component: 'zk_server',
            operation: AdcmHostComponentMapRuleAction.Add,
          },
        ],
      },
      kind: 'flat',
      sort: 'editableFirst',
    };

    const relations = relationsFor(viewConfig, pairsAlphaZkServer);
    const alphaPair = relations.pairs.get(`${zkServer.id}_${hostAlpha.id}`);
    const betaPair = relations.pairs.get(`${zkServer.id}_${hostBeta.id}`);
    expect(alphaPair?.unmap.denyReasons.length).toBeGreaterThan(0);
    expect(betaPair?.unmap.denyReasons).toEqual([]);
    expect(localPairs).toContainEqual({ hostId: hostBeta.id, componentId: zkServer.id });
    expect(hostAlpha.id).toBe(1);
  });

  test('wizard view-model: grouped, editableFirst', () => {
    const viewConfig: MappingViewConfig = {
      strategy: {
        type: 'actionRules',
        rules: [
          {
            service: 'zookeeper',
            component: 'zk_server',
            operation: AdcmHostComponentMapRuleAction.Add,
          },
        ],
      },
      kind: 'services',
      sort: 'editableFirst',
    };
    const { viewModel } = buildView([], viewConfig, []);
    expect(viewModel.kind).toBe('services');
    if (viewModel.kind === 'services') {
      expect(viewModel.services[0].service.name).toBe('zookeeper');
    }
  });

  test('action dialog view-model: flat, editableFirst', () => {
    const viewConfig: MappingViewConfig = {
      strategy: {
        type: 'actionRules',
        rules: [
          {
            service: 'zookeeper',
            component: 'zk_server',
            operation: AdcmHostComponentMapRuleAction.Add,
          },
        ],
      },
      kind: 'flat',
      sort: 'editableFirst',
    };
    const { viewModel } = buildView([], viewConfig, []);
    expect(viewModel.kind).toBe('flat');
    if (viewModel.kind === 'flat') {
      expect(viewModel.components[0].component.name).toBe('zk_server');
    }
  });

  test('viewModel preserves hasErrors from validate', () => {
    const viewConfig: MappingViewConfig = {
      strategy: { type: 'cluster' },
      kind: 'services',
      sort: 'name',
    };
    const { viewModel, model } = buildView(pairsAlphaZkServer, viewConfig);

    const hbaseModel = model.servicesMapping.find((sm) => sm.service.name === 'hbase');
    expect(hbaseModel?.hasErrors).toBe(true);

    expect(viewModel.kind).toBe('services');
    if (viewModel.kind === 'services') {
      const hbaseVm = viewModel.services.find((sm) => sm.service.name === 'hbase');
      expect(hbaseVm?.hasErrors).toBe(true);
    }
  });
});
