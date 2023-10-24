import { AdcmHostShortView, AdcmComponent, AdcmMaintenanceMode, AdcmMapping } from '@models/adcm';
import { HostMapping, ServiceMapping } from './ClusterMapping.types';
import { getComponentsMapping, getHostsMapping, getServicesMapping, mapHostsToComponent } from './ClusterMapping.utils';
import { arrayToHash } from '@utils/arrayUtils';
import { validateConstraints } from './ClusterMapping.utils';

const emptyMapping: AdcmMapping[] = [];

const mapping: AdcmMapping[] = [
  { hostId: 1, componentId: 1 },
  { hostId: 1, componentId: 2 },
  { hostId: 3, componentId: 3 },
];

const services = [
  {
    id: 1,
    name: 'service 1',
    displayName: 'Service 1',
  },
  {
    id: 2,
    name: 'service 2',
    displayName: 'Service 2',
  },
];

const hosts: AdcmHostShortView[] = [
  {
    id: 1,
    name: 'h1',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
  },
  {
    id: 2,
    name: 'h2',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
  },
  {
    id: 3,
    name: 'h3',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
  },
];

const components: AdcmComponent[] = [
  {
    id: 1,
    name: 'component 1',
    displayName: 'Component 1',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
    constraints: [0, 1],
    dependOn: null,
    service: services[0],
  },
  {
    id: 2,
    name: 'component 2',
    displayName: 'Component 2',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
    constraints: [0, 1],
    dependOn: null,
    service: services[0],
  },
  {
    id: 3,
    name: 'service 3',
    displayName: 'Service 3',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
    constraints: [0, 1],
    dependOn: null,
    service: services[1],
  },
];

const componentsDictionary = arrayToHash(components, (c) => c.id);
const hostsDictionary = arrayToHash(hosts, (h) => h.id);

describe('Cluster mapping utils', () => {
  test('test getHostsMapping empty mapping', () => {
    const hostsMapping = getHostsMapping(emptyMapping, hosts, componentsDictionary);

    const expected: HostMapping[] = [
      {
        host: hosts[0],
        components: [],
      },
      {
        host: hosts[1],
        components: [],
      },
      {
        host: hosts[2],
        components: [],
      },
    ];

    expect(hostsMapping).toStrictEqual(expected);
  });

  test('test getHostsMapping', () => {
    const hostsMapping = getHostsMapping(mapping, hosts, componentsDictionary);

    const expected: HostMapping[] = [
      {
        host: hosts[0],
        components: [components[0], components[1]],
      },
      {
        host: hosts[1],
        components: [],
      },
      {
        host: hosts[2],
        components: [components[2]],
      },
    ];

    expect(hostsMapping).toStrictEqual(expected);
  });

  test('test getServicesMapping empty mapping', () => {
    const componentsMapping = getComponentsMapping(emptyMapping, components, hostsDictionary);
    const servicesMapping = getServicesMapping(componentsMapping);

    const expected: ServiceMapping[] = [
      {
        service: services[0],
        componentsMapping: [
          {
            component: components[0],
            hosts: [],
          },
          {
            component: components[1],
            hosts: [],
          },
        ],
      },
      {
        service: services[1],
        componentsMapping: [
          {
            component: components[2],
            hosts: [],
          },
        ],
      },
    ];

    expect(servicesMapping).toStrictEqual(expected);
  });

  test('test getServicesMapping mapping', () => {
    const componentsMapping = getComponentsMapping(mapping, components, hostsDictionary);
    const servicesMapping = getServicesMapping(componentsMapping);

    const expected: ServiceMapping[] = [
      {
        service: services[0],
        componentsMapping: [
          {
            component: components[0],
            hosts: [hosts[0]],
          },
          {
            component: components[1],
            hosts: [hosts[0]],
          },
        ],
      },
      {
        service: services[1],
        componentsMapping: [
          {
            component: components[2],
            hosts: [hosts[2]],
          },
        ],
      },
    ];

    expect(servicesMapping).toStrictEqual(expected);
  });

  test('test mapHostsToComponent', () => {
    const componentsMapping = getComponentsMapping(mapping, components, hostsDictionary);
    const servicesMapping = getServicesMapping(componentsMapping);
    const newMapping = mapHostsToComponent(servicesMapping, [hosts[1]], components[0]);

    const expected: AdcmMapping[] = [
      { hostId: 1, componentId: 2 },
      { hostId: 2, componentId: 1 },
      { hostId: 3, componentId: 3 },
    ];

    expect(newMapping).toEqual(expect.arrayContaining(expected));
  });

  test('test validateConstraints', () => {
    // Check all hosts constraints
    expect(validateConstraints(['+'], 2, 0)).toEqual({
      isValid: false,
      error: 'Component should be installed on all hosts of cluster.',
    });
    expect(validateConstraints(['+'], 2, 1)).toEqual({
      isValid: false,
      error: 'Component should be installed on all hosts of cluster.',
    });
    expect(validateConstraints(['+'], 2, 2)).toEqual({ isValid: true });

    // Check range constraints
    expect(validateConstraints([0, 1], 2, 0)).toEqual({ isValid: true });
    expect(validateConstraints([0, 1], 2, 1)).toEqual({ isValid: true });
    expect(validateConstraints([0, 1], 2, 2)).toEqual({
      isValid: false,
      error: 'From 0 to 1 components should be installed.',
    });
    expect(validateConstraints([3, 10], 5, 5)).toEqual({ isValid: true });

    expect(validateConstraints([0, '+'], 5, 0)).toEqual({ isValid: true });
    expect(validateConstraints([1, '+'], 5, 0)).toEqual({
      isValid: false,
      error: '1 or more components should be installed.',
    });
    expect(validateConstraints([2, '+'], 5, 1)).toEqual({
      isValid: false,
      error: '2 or more components should be installed.',
    });

    // Check exact constraints
    expect(validateConstraints([1], 2, 0)).toEqual({
      isValid: false,
      error: 'Exactly 1 component should be installed.',
    });
    expect(validateConstraints([1], 2, 1)).toEqual({ isValid: true });
    expect(validateConstraints([2], 2, 2)).toEqual({ isValid: true });
    expect(validateConstraints([1], 2, 2)).toEqual({
      isValid: false,
      error: 'Exactly 1 component should be installed.',
    });

    // Check odd constraints
    expect(validateConstraints(['odd'], 4, 3)).toEqual({ isValid: true });
    expect(validateConstraints([1, 'odd'], 4, 3)).toEqual({ isValid: true });
    expect(validateConstraints([1, 'odd'], 4, 2)).toEqual({
      isValid: false,
      error: '1 or more components should be installed. Total amount should be odd.',
    });
  });
});
