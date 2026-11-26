import { act, renderHook } from '@testing-library/react';
import { AdcmHostComponentMapRuleAction, type AdcmMapping } from '@models/adcm';
import { useMappingEditor } from './useMappingEditor';
import type { MappingViewConfig } from '@utils/mapping/mapping.types';
import { makePairKey } from '@utils/mapping/componentHostRelations';
import {
  components,
  hostAlpha,
  hostBeta,
  hostGamma,
  hosts,
  pairsAlphaZkServer,
  zkServer,
} from '@utils/mapping/__fixtures__/mappingFixtures';

const emptyMapping: AdcmMapping[] = [];
const emptyNotAddedServices = {};

const clusterViewConfig: MappingViewConfig = {
  strategy: { type: 'cluster' },
  kind: 'services',
  sort: 'name',
};

const addOnlyZkServerConfig: MappingViewConfig = {
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

describe('useMappingEditor', () => {
  test('map host updates localMapping and services viewModel', () => {
    const { result } = renderHook(() =>
      useMappingEditor(pairsAlphaZkServer, hosts, components, emptyNotAddedServices, true, clusterViewConfig),
    );

    expect(result.current.localMapping).toEqual(pairsAlphaZkServer);
    expect(result.current.isMappingChanged).toBe(false);

    act(() => {
      result.current.handleMapHostsToComponent([hostAlpha, hostBeta], zkServer);
    });

    expect(result.current.isMappingChanged).toBe(true);
    expect(result.current.localMapping).toEqual(
      expect.arrayContaining([
        { hostId: hostAlpha.id, componentId: zkServer.id },
        { hostId: hostBeta.id, componentId: zkServer.id },
      ]),
    );
    expect(result.current.viewModel?.kind).toBe('services');
    if (result.current.viewModel?.kind === 'services') {
      const zk = result.current.viewModel.services.find((sm) => sm.service.name === 'zookeeper');
      const zkServerMapping = zk?.componentsMapping.find((cm) => cm.component.id === zkServer.id);
      expect(zkServerMapping?.hosts.map((h) => h.id).sort()).toEqual([hostAlpha.id, hostBeta.id].sort());
    }
  });

  test('unmap removes pair and reset restores baseline', () => {
    const { result } = renderHook(() =>
      useMappingEditor(pairsAlphaZkServer, hosts, components, emptyNotAddedServices, true, clusterViewConfig),
    );

    act(() => {
      result.current.handleMapHostsToComponent([hostAlpha, hostBeta], zkServer);
    });
    act(() => {
      result.current.handleUnmap(hostBeta.id, zkServer.id);
    });

    expect(result.current.localMapping).toEqual([{ hostId: hostAlpha.id, componentId: zkServer.id }]);

    act(() => {
      result.current.handleReset();
    });

    expect(result.current.localMapping).toEqual(pairsAlphaZkServer);
    expect(result.current.isMappingChanged).toBe(false);
  });

  test('filter change updates mappingFilter', () => {
    const { result } = renderHook(() =>
      useMappingEditor(pairsAlphaZkServer, hosts, components, emptyNotAddedServices, true, clusterViewConfig),
    );

    act(() => {
      result.current.handleMappingFilterChange({ hostName: 'alpha' });
    });

    expect(result.current.mappingFilter.hostName).toBe('alpha');
  });

  test('Add-only: newly mapped host can unmap; baseline host cannot', () => {
    const { result } = renderHook(() =>
      useMappingEditor(emptyMapping, hosts, components, emptyNotAddedServices, true, addOnlyZkServerConfig),
    );

    act(() => {
      result.current.handleMapHostsToComponent([hostBeta], zkServer);
    });

    expect(result.current.localMapping).toEqual([{ hostId: hostBeta.id, componentId: zkServer.id }]);
    const betaKey = makePairKey(zkServer.id, hostBeta.id);
    expect(result.current.relations?.pairs.get(betaKey)?.unmap.denyReasons).toEqual([]);
  });

  test('Add-only: baseline host unmap is denied in relations', () => {
    const { result } = renderHook(() =>
      useMappingEditor(pairsAlphaZkServer, hosts, components, emptyNotAddedServices, true, addOnlyZkServerConfig),
    );

    const alphaKey = makePairKey(zkServer.id, hostAlpha.id);
    expect(result.current.relations?.pairs.get(alphaKey)?.unmap.denyReasons.length).toBeGreaterThan(0);
  });

  test('relations is undefined until loaded', () => {
    const { result } = renderHook(() =>
      useMappingEditor(pairsAlphaZkServer, hosts, components, emptyNotAddedServices, false, clusterViewConfig),
    );

    expect(result.current.relations).toBeUndefined();
  });

  test('relations stay stable after local unmap', () => {
    const baselineGammaZk: AdcmMapping[] = [{ hostId: hostGamma.id, componentId: zkServer.id }];
    const zkComponents = [zkServer];
    const { result } = renderHook(() =>
      useMappingEditor(baselineGammaZk, hosts, zkComponents, emptyNotAddedServices, true, clusterViewConfig),
    );

    const key = makePairKey(zkServer.id, hostGamma.id);
    const relationsBefore = result.current.relations;
    expect(relationsBefore?.pairs.get(key)?.map.denyReasons).toEqual([]);

    act(() => {
      result.current.handleUnmap(hostGamma.id, zkServer.id);
    });

    expect(result.current.localMapping).toEqual([]);
    expect(result.current.relations).toBe(relationsBefore);
    expect(result.current.relations?.pairs.get(key)?.map.denyReasons).toEqual([]);
  });

  test('sortDirection change keeps mappingErrors and availability references', () => {
    const { result } = renderHook(() =>
      useMappingEditor(pairsAlphaZkServer, hosts, components, emptyNotAddedServices, true, clusterViewConfig),
    );

    const errorsBefore = result.current.mappingErrors;
    const availabilityBefore = result.current.availability;
    const relationsBefore = result.current.relations;
    const viewModelBefore = result.current.viewModel;

    act(() => {
      result.current.handleMappingSortDirectionChange('desc');
    });

    expect(result.current.mappingSortDirection).toBe('desc');
    expect(result.current.mappingErrors).toBe(errorsBefore);
    expect(result.current.availability).toBe(availabilityBefore);
    expect(result.current.relations).toBe(relationsBefore);
    expect(result.current.viewModel).not.toBe(viewModelBefore);
  });
});
