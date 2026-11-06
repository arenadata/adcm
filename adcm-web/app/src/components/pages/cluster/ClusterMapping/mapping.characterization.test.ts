/* eslint-disable spellcheck/spell-checker */
import { AdcmHostComponentMapRuleAction } from '@models/adcm';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';
import { arrayToHash } from '@utils/arrayUtils';
import {
  hostAlpha,
  hostBeta,
  hostGamma,
  hosts,
  components,
  zkServer,
  zkClient,
  hbaseMaster,
  pairsAlphaZkServer,
  zkClientDependingOnZkServer,
} from '@utils/mapping/__fixtures__/mappingFixtures';
import {
  checkComponentActionsMappingAvailability,
  checkHostActionsMappingAvailability,
  checkHostActionsUnmappingAvailability,
  getComponentMapActions as getActionComponentMapActions,
  sortExtendedComponentsMapping,
} from '@commonComponents/DynamicActionDialog/DynamicActionSteps/DynamicActionHostMapping/DynamicActionHostMapping.utils';
import {
  getComponentMapActions as getWizardComponentMapActions,
  sortExtendedActionWizardServicesMapping,
} from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMapping.utils';
import { applyMappingDelta } from '@utils/mapping/applyMappingDelta';
import {
  checkComponentMappingAvailability,
  checkHostMappingAvailability,
  checkHostUnmappingAvailability,
  getComponentsMapping,
  getHostsMapping,
  getInitiallyMappedComponentsDictionary,
  getInitiallyMappedHostsDictionary,
  getServicesMapping,
  validate,
} from './ClusterMapping.utils';

const addZkServerRules: AdcmActionProcessMappingStepRules[] = [
  {
    operation: AdcmHostComponentMapRuleAction.Add,
    component: 'zk_server',
    service: 'zookeeper',
    description: '',
    required: false,
  },
];

const hostsDictionary = arrayToHash(hosts, (h) => h.id);
const componentsDictionary = arrayToHash(components, (c) => c.id);

describe('mapping characterization model', () => {
  test('getServicesMapping groups components under their service even when unmapped', () => {
    const { componentsMapping } = getComponentsMapping([], components, hostsDictionary);
    const services = getServicesMapping(componentsMapping, { sortBy: 'name', sortDirection: 'asc' });
    expect(services.map((s) => s.service.name)).toEqual(['hbase', 'zookeeper']);
  });

  test('getHostsMapping keeps hosts with empty component lists', () => {
    const result = getHostsMapping([], hosts, componentsDictionary);
    expect(result).toHaveLength(hosts.length);
    expect(result.every((h) => h.components.length === 0)).toBe(true);
  });

  test('getComponentsMapping maps alpha to zk_server and leaves other components empty', () => {
    const { componentsMapping } = getComponentsMapping(pairsAlphaZkServer, components, hostsDictionary);
    const byName = arrayToHash(componentsMapping, (cm) => cm.component.name);

    expect(byName.zk_server.hosts.map((h) => h.name)).toEqual(['alpha']);
    expect(byName.zk_client.hosts).toEqual([]);
    expect(byName.hbase_master.hosts).toEqual([]);
    expect(byName.hbase_client.hosts).toEqual([]);
  });
});

describe('mapping characterization cluster availability', () => {
  test('cluster: component of installed service is not available', () => {
    const errors = checkComponentMappingAvailability(hbaseMaster);
    expect(errors.componentNotAvailableError).toBeDefined();
  });

  test('cluster: component of created service is available', () => {
    const errors = checkComponentMappingAvailability(zkServer);
    expect(errors.componentNotAvailableError).toBeUndefined();
  });

  test('cluster: host in maintenance cannot be added unless initially mapped', () => {
    expect(checkHostMappingAvailability(hostGamma)).toBeDefined();
    expect(checkHostMappingAvailability(hostGamma, new Set([hostGamma.id]))).toBeUndefined();
  });

  test('cluster: unmap is always allowed', () => {
    expect(checkHostUnmappingAvailability(hostGamma)).toBeUndefined();
  });
});

describe('mapping characterization action/wizard availability and sort', () => {
  const emptyComponentsMapping = getComponentsMapping([], components, hostsDictionary).componentsMapping;
  const servicesMapping = getServicesMapping(emptyComponentsMapping, { sortBy: 'name', sortDirection: 'asc' });

  test('action: component without rules is not available', () => {
    const errors = checkComponentActionsMappingAvailability(zkClient, new Set());
    expect(errors.componentNotAvailableError).toBeDefined();
  });

  test('action: newly added host can be unmapped without Remove rule', () => {
    const allow = new Set([AdcmHostComponentMapRuleAction.Add]);
    expect(checkHostActionsUnmappingAvailability(hostAlpha, allow, new Set())).toBeUndefined();
  });

  test('wizard: services with editable components come first, then name', () => {
    const laid = sortExtendedActionWizardServicesMapping(servicesMapping, addZkServerRules, 'asc');
    expect(laid[0].service.name).toBe('zookeeper');
    expect(laid[0].isAllowedActions).toBe(true);
    expect(laid[1].isAllowedActions).toBe(false);
  });

  test('dynamic action: flat list, no service grouping, editable first', () => {
    const flat = sortExtendedComponentsMapping(servicesMapping, {
      hostComponentMapRules: [
        { action: AdcmHostComponentMapRuleAction.Add, service: 'zookeeper', component: 'zk_server' },
      ],
    });

    expect(flat[0].component.name).toBe('zk_server');
    expect(flat.every((item) => 'component' in item && !('componentsMapping' in item))).toBe(true);
  });

  test('action: host without Add rule cannot be added unless initially mapped', () => {
    const allowRemove = new Set([AdcmHostComponentMapRuleAction.Remove]);
    expect(checkHostActionsMappingAvailability(hostAlpha, allowRemove, new Set())).toBeDefined();
    expect(checkHostActionsMappingAvailability(hostAlpha, allowRemove, new Set([hostAlpha.id]))).toBeUndefined();
  });

  test('action: host in maintenance cannot be added unless initially mapped', () => {
    const allowAdd = new Set([AdcmHostComponentMapRuleAction.Add]);
    expect(checkHostActionsMappingAvailability(hostGamma, allowAdd, new Set())).toBeDefined();
    expect(checkHostActionsMappingAvailability(hostGamma, allowAdd, new Set([hostGamma.id]))).toBeUndefined();
  });

  test('action: host with Add rule and MM off can be added', () => {
    const allowAdd = new Set([AdcmHostComponentMapRuleAction.Add]);
    expect(checkHostActionsMappingAvailability(hostAlpha, allowAdd, new Set())).toBeUndefined();
  });

  test('action: initially mapped host cannot be unmapped without Remove rule', () => {
    const allowAdd = new Set([AdcmHostComponentMapRuleAction.Add]);
    expect(checkHostActionsUnmappingAvailability(hostAlpha, allowAdd, new Set([hostAlpha.id]))).toBeDefined();
  });

  test('action getComponentMapActions matches service.name and component.name', () => {
    const details = {
      hostComponentMapRules: [
        { action: AdcmHostComponentMapRuleAction.Add, service: 'zookeeper', component: 'zk_server' },
        { action: AdcmHostComponentMapRuleAction.Remove, service: 'zookeeper', component: 'zk_server' },
        { action: AdcmHostComponentMapRuleAction.Add, service: 'hbase', component: 'hbase_master' },
      ],
    };

    const zkServerActions = getActionComponentMapActions(details, zkServer.service, zkServer);
    expect(zkServerActions.has(AdcmHostComponentMapRuleAction.Add)).toBe(true);
    expect(zkServerActions.has(AdcmHostComponentMapRuleAction.Remove)).toBe(true);

    const zkClientActions = getActionComponentMapActions(details, zkClient.service, zkClient);
    expect(zkClientActions.size).toBe(0);

    const hbaseMasterActions = getActionComponentMapActions(details, hbaseMaster.service, hbaseMaster);
    expect([...hbaseMasterActions]).toEqual([AdcmHostComponentMapRuleAction.Add]);
  });

  test('wizard getComponentMapActions matches operation by service and component names', () => {
    const rules = [
      {
        operation: AdcmHostComponentMapRuleAction.Remove,
        component: 'zk_server',
        service: 'zookeeper',
        description: '',
        required: false,
      },
    ];

    expect(
      getWizardComponentMapActions(rules, zkServer.service, zkServer).has(AdcmHostComponentMapRuleAction.Remove),
    ).toBe(true);
    expect(getWizardComponentMapActions(rules, zkClient.service, zkClient).size).toBe(0);
  });

  test('wizard: desc reverses the editable-first order', () => {
    const asc = sortExtendedActionWizardServicesMapping(servicesMapping, addZkServerRules, 'asc');
    const desc = sortExtendedActionWizardServicesMapping(servicesMapping, addZkServerRules, 'desc');

    expect(asc.map((s) => s.service.name)).toEqual(['zookeeper', 'hbase']);
    expect(desc.map((s) => s.service.name)).toEqual(['hbase', 'zookeeper']);
  });
});

describe('mapping characterization initially mapped dictionaries', () => {
  test('getInitiallyMappedHostsDictionary groups host ids by component', () => {
    const result = getInitiallyMappedHostsDictionary([
      ...pairsAlphaZkServer,
      { hostId: hostBeta.id, componentId: zkServer.id },
      { hostId: hostAlpha.id, componentId: zkClient.id },
    ]);

    expect([...result[zkServer.id]].sort()).toEqual([hostAlpha.id, hostBeta.id]);
    expect([...result[zkClient.id]]).toEqual([hostAlpha.id]);
    expect(result[hbaseMaster.id]).toBeUndefined();
  });

  test('getInitiallyMappedComponentsDictionary groups component ids by host', () => {
    const result = getInitiallyMappedComponentsDictionary([
      ...pairsAlphaZkServer,
      { hostId: hostAlpha.id, componentId: zkClient.id },
    ]);

    expect([...result[hostAlpha.id]].sort()).toEqual([zkClient.id, zkServer.id].sort());
    expect(result[hostBeta.id]).toBeUndefined();
  });

  test('empty mapping yields empty dictionaries', () => {
    expect(getInitiallyMappedHostsDictionary([])).toEqual({});
    expect(getInitiallyMappedComponentsDictionary([])).toEqual({});
  });
});

describe('mapping characterization applyMappingDelta', () => {
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

describe('mapping characterization optional dependOn', () => {
  test('optional [0, +] with zero hosts skips dependOn even if required component is unmapped', () => {
    const optionalAndRequired = [zkServer, zkClientDependingOnZkServer];
    const { componentsMapping } = getComponentsMapping([], optionalAndRequired, hostsDictionary);
    const servicesMapping = getServicesMapping(componentsMapping, { sortBy: 'name', sortDirection: 'asc' });
    const errors = validate(componentsMapping, {
      allHostsCount: hosts.length,
      servicesMappingDictionary: arrayToHash(servicesMapping, (sm) => sm.service.prototype.id),
      notAddedServicesDictionary: {},
    });

    expect(errors[zkClientDependingOnZkServer.id]).toBeUndefined();
    expect(errors[zkServer.id]?.constraintsError).toBeDefined();
    expect(errors[zkServer.id]?.dependenciesErrors).toBeUndefined();
  });

  test('optional [0, +] with hosts mapped still validates dependOn', () => {
    const optionalAndRequired = [zkServer, zkClientDependingOnZkServer];
    const { componentsMapping } = getComponentsMapping(
      [{ hostId: hostAlpha.id, componentId: zkClientDependingOnZkServer.id }],
      optionalAndRequired,
      hostsDictionary,
    );
    const servicesMapping = getServicesMapping(componentsMapping, { sortBy: 'name', sortDirection: 'asc' });
    const errors = validate(componentsMapping, {
      allHostsCount: hosts.length,
      servicesMappingDictionary: arrayToHash(servicesMapping, (sm) => sm.service.prototype.id),
      notAddedServicesDictionary: {},
    });

    expect(errors[zkClientDependingOnZkServer.id]?.dependenciesErrors?.requiredErrors).toBeDefined();
  });
});
