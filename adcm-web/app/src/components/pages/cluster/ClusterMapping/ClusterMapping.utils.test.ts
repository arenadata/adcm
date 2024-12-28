/* eslint-disable spellcheck/spell-checker */
import type { AdcmMappingComponent, AdcmMapping, AdcmLicenseStatus, AdcmPrototypeType } from '@models/adcm';
import { AdcmMaintenanceMode } from '@models/adcm';
import type { HostMapping, ComponentsMappingErrors, ServiceMapping, ValidateRelatedData } from './ClusterMapping.types';
import {
  getComponentsMapping,
  getHostsMapping,
  getServicesMapping,
  mapHostsToComponent,
  mapComponentsToHost,
  getConstraintsLimit,
  validate,
  validateConstraints,
} from './ClusterMapping.utils';
import { arrayToHash } from '@utils/arrayUtils';

const servicesDictionaryByName = {
  HBase: {
    id: 1,
    name: 'hbase',
    displayName: 'HBase',
    state: 'created',
    prototype: {
      id: 6,
      name: 'hbase',
      displayName: 'HBase',
      version: '2.2.7',
    },
  },
  Zookeeper: {
    id: 2,
    name: 'zookeeper',
    displayName: 'Zookeeper',
    state: 'created',
    prototype: {
      id: 19,
      name: 'zookeeper',
      displayName: 'Zookeeper',
      version: '3.5.10',
    },
  },
};

const candidateServicesDictionaryByName = {
  HDFS: {
    id: 7,
    name: 'hdfs',
    displayName: 'HDFS',
    version: '3.1.2',
    isRequired: false,
    dependOn: null,
    type: 'service' as AdcmPrototypeType.Service,
    license: {
      status: 'absent' as AdcmLicenseStatus,
      text: null,
    },
  },
};

const hostsDictionaryByName = {
  host1: {
    id: 1,
    name: 'host 1',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
  },
  host2: {
    id: 2,
    name: 'host 2',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
  },
  host3: {
    id: 3,
    name: 'host 3',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
  },
};

const hosts = [hostsDictionaryByName.host1, hostsDictionaryByName.host2, hostsDictionaryByName.host3];

const componentsDictionaryByName = {
  hBaseClient: {
    id: 1,
    name: 'client',
    displayName: 'HBase Client',
    isMaintenanceModeAvailable: true,
    maintenanceMode: 'off' as AdcmMaintenanceMode,
    constraints: [0, '+'],
    prototype: {
      id: 32,
      name: 'client',
      displayName: 'HBase Client',
      version: '2.2.7',
    },
    dependOn: [
      {
        servicePrototype: {
          id: 19,
          name: 'zookeeper',
          displayName: 'Zookeeper',
          version: '3.5.10',
          license: {
            status: 'absent' as AdcmLicenseStatus,
            text: null,
          },
          componentPrototypes: [
            {
              id: 73,
              name: 'SERVER',
              displayName: 'Zookeeper Server',
              version: '3.5.10',
            },
          ],
        },
      },
      {
        servicePrototype: {
          id: 7,
          name: 'hdfs',
          displayName: 'HDFS',
          version: '3.1.2',
          license: {
            status: 'absent' as AdcmLicenseStatus,
            text: null,
          },
          componentPrototypes: [
            {
              id: 39,
              name: 'namenode',
              displayName: 'HDFS NameNode',
              version: '3.1.2',
            },
          ],
        },
      },
    ],
    service: servicesDictionaryByName.HBase,
  },
  hBaseMaster: {
    id: 2,
    name: 'master',
    displayName: 'HBase Master Server',
    isMaintenanceModeAvailable: true,
    maintenanceMode: 'off' as AdcmMaintenanceMode,
    constraints: [1, '+'],
    prototype: {
      id: 33,
      name: 'master',
      displayName: 'HBase Master Server',
      version: '2.2.7',
    },
    dependOn: [
      {
        servicePrototype: {
          id: 19,
          name: 'zookeeper',
          displayName: 'Zookeeper',
          version: '3.5.10',
          license: {
            status: 'absent' as AdcmLicenseStatus,
            text: null,
          },
          componentPrototypes: [
            {
              id: 73,
              name: 'SERVER',
              displayName: 'Zookeeper Server',
              version: '3.5.10',
            },
          ],
        },
      },
      {
        servicePrototype: {
          id: 7,
          name: 'hdfs',
          displayName: 'HDFS',
          version: '3.1.2',
          license: {
            status: 'absent' as AdcmLicenseStatus,
            text: null,
          },
          componentPrototypes: [
            {
              id: 39,
              name: 'namenode',
              displayName: 'HDFS NameNode',
              version: '3.1.2',
            },
          ],
        },
      },
    ],
    service: servicesDictionaryByName.HBase,
  },
  zookeeperServer: {
    id: 7,
    name: 'SERVER',
    displayName: 'Zookeeper Server',
    isMaintenanceModeAvailable: true,
    maintenanceMode: 'off' as AdcmMaintenanceMode,
    constraints: ['odd'],
    prototype: {
      id: 73,
      name: 'SERVER',
      displayName: 'Zookeeper Server',
      version: '3.5.10',
    },
    dependOn: null,
    service: servicesDictionaryByName.Zookeeper,
  },
};

const components: AdcmMappingComponent[] = [
  componentsDictionaryByName.hBaseClient,
  componentsDictionaryByName.hBaseMaster,
  componentsDictionaryByName.zookeeperServer,
];
const emptyMapping: AdcmMapping[] = [];

const componentsDictionary = arrayToHash(components, (c) => c.id);
const hostsDictionary = arrayToHash(hosts, (h) => h.id);

describe('Cluster mapping utils', () => {
  test('test getHostsMapping empty mapping', () => {
    const mapping: AdcmMapping[] = [];
    const hostsMapping = getHostsMapping(mapping, hosts, componentsDictionary);

    const expected: HostMapping[] = [
      {
        host: hostsDictionaryByName.host1,
        components: [],
      },
      {
        host: hostsDictionaryByName.host2,
        components: [],
      },
      {
        host: hostsDictionaryByName.host3,
        components: [],
      },
    ];

    expect(hostsMapping).toStrictEqual(expected);
  });

  test('test getHostsMapping', () => {
    const mapping: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseMaster.id },
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    const hostsMapping = getHostsMapping(mapping, hosts, componentsDictionary);

    const expected: HostMapping[] = [
      {
        host: hostsDictionaryByName.host1,
        components: [componentsDictionaryByName.hBaseClient, componentsDictionaryByName.hBaseMaster],
      },
      {
        host: hostsDictionaryByName.host2,
        components: [],
      },
      {
        host: hostsDictionaryByName.host3,
        components: [componentsDictionaryByName.zookeeperServer],
      },
    ];

    expect(hostsMapping).toStrictEqual(expected);
  });

  test('test getServicesMapping empty mapping', () => {
    const componentsMapping = getComponentsMapping(emptyMapping, components, hostsDictionary);
    const servicesMapping = getServicesMapping(componentsMapping);

    const expected: ServiceMapping[] = [
      {
        service: servicesDictionaryByName.HBase,
        componentsMapping: [
          {
            component: componentsDictionaryByName.hBaseClient,
            hosts: [],
          },
          {
            component: componentsDictionaryByName.hBaseMaster,
            hosts: [],
          },
        ],
      },
      {
        service: servicesDictionaryByName.Zookeeper,
        componentsMapping: [
          {
            component: componentsDictionaryByName.zookeeperServer,
            hosts: [],
          },
        ],
      },
    ];

    expect(servicesMapping).toStrictEqual(expected);
  });

  test('test getServicesMapping mapping', () => {
    const mapping: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseMaster.id },
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    const componentsMapping = getComponentsMapping(mapping, components, hostsDictionary);
    const servicesMapping = getServicesMapping(componentsMapping);

    const expected: ServiceMapping[] = [
      {
        service: servicesDictionaryByName.HBase,
        componentsMapping: [
          {
            component: componentsDictionaryByName.hBaseClient,
            hosts: [hostsDictionaryByName.host1],
          },
          {
            component: componentsDictionaryByName.hBaseMaster,
            hosts: [hostsDictionaryByName.host1],
          },
        ],
      },
      {
        service: servicesDictionaryByName.Zookeeper,
        componentsMapping: [
          {
            component: componentsDictionaryByName.zookeeperServer,
            hosts: [hostsDictionaryByName.host3],
          },
        ],
      },
    ];

    expect(servicesMapping).toStrictEqual(expected);
  });

  test('test mapHostsToComponent', () => {
    const mapping: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseMaster.id },
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    // moving hbaseMaster from host1 to host2
    const newMapping = mapHostsToComponent(
      mapping,
      [hostsDictionaryByName.host2],
      componentsDictionaryByName.hBaseMaster,
    );

    const expected: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host2.id, componentId: componentsDictionaryByName.hBaseMaster.id },
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    expect(newMapping).toEqual(expect.arrayContaining(expected));
  });

  test('test mapComponentsToHost', () => {
    const mapping: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseMaster.id },
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    // moving hbaseMaster from host1 to host2
    const newMapping = mapComponentsToHost(
      mapping,
      [componentsDictionaryByName.hBaseMaster],
      hostsDictionaryByName.host2,
    );

    const expected: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host2.id, componentId: componentsDictionaryByName.hBaseMaster.id },
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    expect(newMapping).toEqual(expect.arrayContaining(expected));
  });

  test('test validateConstraints', () => {
    // Check all hosts constraints
    expect(validateConstraints(['+'], 2, 0)).toEqual({
      type: 'constraint',
      message: 'Component should be mapped on all hosts of cluster.',
    });
    expect(validateConstraints(['+'], 2, 1)).toEqual({
      type: 'constraint',
      message: 'Component should be mapped on all hosts of cluster.',
    });
    expect(validateConstraints(['+'], 2, 2)).toBeUndefined();

    // Check range constraints
    expect(validateConstraints([0, 1], 2, 0)).toBeUndefined();
    expect(validateConstraints([0, 1], 2, 1)).toBeUndefined();
    expect(validateConstraints([0, 1], 2, 2)).toEqual({
      type: 'constraint',
      message: 'From 0 to 1 components should be mapped.',
    });
    expect(validateConstraints([3, 10], 5, 5)).toBeUndefined();

    expect(validateConstraints([0, '+'], 5, 0)).toBeUndefined();
    expect(validateConstraints([1, '+'], 5, 0)).toEqual({
      type: 'constraint',
      message: '1 or more components should be mapped.',
    });
    expect(validateConstraints([2, '+'], 5, 1)).toEqual({
      type: 'constraint',
      message: '2 or more components should be mapped.',
    });

    // Check exact constraints
    expect(validateConstraints([1], 2, 0)).toEqual({
      type: 'constraint',
      message: 'Exactly 1 component should be mapped.',
    });
    expect(validateConstraints([1], 2, 1)).toBeUndefined();
    expect(validateConstraints([2], 2, 2)).toBeUndefined();
    expect(validateConstraints([1], 2, 2)).toEqual({
      type: 'constraint',
      message: 'Exactly 1 component should be mapped.',
    });

    // Check odd constraints
    expect(validateConstraints(['odd'], 4, 3)).toBeUndefined();
    expect(validateConstraints([1, 'odd'], 4, 3)).toBeUndefined();
    expect(validateConstraints([1, 'odd'], 4, 2)).toEqual({
      type: 'constraint',
      message: '1 or more components should be mapped. Total amount should be odd.',
    });
  });

  test('test getConstraintsLimit', () => {
    expect(getConstraintsLimit(['odd'])).toBe(1);
    expect(getConstraintsLimit([1, 22])).toBe(22);
    expect(getConstraintsLimit([42])).toBe(42);
    expect(getConstraintsLimit([42, '+'])).toBe(42);
  });

  test('test validate constraints', () => {
    const mapping: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    const componentMapping = getComponentsMapping(mapping, components, hostsDictionary);
    const serviceMapping = getServicesMapping(componentMapping);
    const servicesMappingDictionary = arrayToHash(serviceMapping, (sm) => sm.service.prototype.id);

    const relatedData: ValidateRelatedData = {
      allHostsCount: hosts.length,
      servicesMappingDictionary,
      notAddedServicesDictionary: {},
    };

    const validationResult = validate(componentMapping, relatedData);

    const expected: ComponentsMappingErrors = {
      [componentsDictionaryByName.hBaseMaster.id]: {
        constraintsError: {
          type: 'constraint',
          message: '1 or more components should be mapped.',
        },
        dependenciesErrors: undefined,
      },
    };

    expect(validationResult).toStrictEqual(expected);
  });

  test('test validate service without component', () => {
    const mapping: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseMaster.id },
      { hostId: hostsDictionaryByName.host3.id, componentId: componentsDictionaryByName.zookeeperServer.id },
    ];

    const componentMapping = getComponentsMapping(mapping, components, hostsDictionary);
    const serviceMapping = getServicesMapping(componentMapping);
    const servicesMappingDictionary = arrayToHash(serviceMapping, (sm) => sm.service.prototype.id);

    const relatedData: ValidateRelatedData = {
      allHostsCount: hosts.length,
      servicesMappingDictionary,
      notAddedServicesDictionary: {},
    };

    const validationResult = validate(componentMapping, relatedData);

    expect(validationResult).toStrictEqual({});
  });

  test('test validate dependOn', () => {
    const mapping: AdcmMapping[] = [
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseClient.id },
      { hostId: hostsDictionaryByName.host1.id, componentId: componentsDictionaryByName.hBaseMaster.id },
    ];

    const componentMapping = getComponentsMapping(mapping, components, hostsDictionary);
    const serviceMapping = getServicesMapping(componentMapping);
    const servicesMappingDictionary = arrayToHash(serviceMapping, (sm) => sm.service.prototype.id);

    const relatedData: ValidateRelatedData = {
      allHostsCount: hosts.length,
      servicesMappingDictionary,
      notAddedServicesDictionary: {
        [candidateServicesDictionaryByName.HDFS.id]: candidateServicesDictionaryByName.HDFS,
      },
    };

    const validationResult = validate(componentMapping, relatedData);

    const expected: ComponentsMappingErrors = {
      [componentsDictionaryByName.zookeeperServer.id]: {
        constraintsError: {
          type: 'constraint',
          message: '1 or more components should be mapped. Total amount should be odd.',
        },
        dependenciesErrors: undefined,
      },
      [componentsDictionaryByName.hBaseClient.id]: {
        constraintsError: undefined,
        dependenciesErrors: {
          requiredErrors: [
            {
              type: 'required',
              params: {
                components: [
                  componentsDictionaryByName.hBaseClient.dependOn[0].servicePrototype.componentPrototypes[0]
                    .displayName,
                ],
                service: servicesDictionaryByName.Zookeeper.displayName,
              },
            },
          ],
          notAddedErrors: [
            {
              type: 'not-added',
              params: {
                service: componentsDictionaryByName.hBaseClient.dependOn![1].servicePrototype,
              },
            },
          ],
        },
      },
      [componentsDictionaryByName.hBaseMaster.id]: {
        constraintsError: undefined,
        dependenciesErrors: {
          requiredErrors: [
            {
              type: 'required',
              params: {
                components: [
                  componentsDictionaryByName.hBaseClient.dependOn[0].servicePrototype.componentPrototypes[0]
                    .displayName,
                ],
                service: servicesDictionaryByName.Zookeeper.displayName,
              },
            },
          ],
          notAddedErrors: [
            {
              type: 'not-added',
              params: {
                service: componentsDictionaryByName.hBaseClient.dependOn![1].servicePrototype,
              },
            },
          ],
        },
      },
    };

    expect(validationResult).toStrictEqual(expected);
  });
});
