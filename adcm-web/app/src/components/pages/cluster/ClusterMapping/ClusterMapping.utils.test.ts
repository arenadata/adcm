/* eslint-disable spellcheck/spell-checker */
import { AdcmHostShortView, AdcmComponent, AdcmMaintenanceMode, AdcmMapping } from '@models/adcm';
import { HostMapping, ServiceMapping, ServiceMappingFilter, HostMappingFilter } from './ClusterMapping.types';
import { getHostsMapping, getServicesMapping, mapComponentsToHost, mapHostsToComponent } from './ClusterMapping.utils';
import { arrayToHash } from '@utils/arrayUtils';
import { validateConstraint } from './ClusterMapping.utils';

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
    constraint: [0, 1],
    dependOn: null,
    service: services[0],
  },
  {
    id: 2,
    name: 'component 2',
    displayName: 'Component 2',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
    constraint: [0, 1],
    dependOn: null,
    service: services[0],
  },
  {
    id: 3,
    name: 'service 3',
    displayName: 'Service 3',
    isMaintenanceModeAvailable: false,
    maintenanceMode: AdcmMaintenanceMode.Off,
    constraint: [0, 1],
    dependOn: null,
    service: services[1],
  },
];

const componentsDictionary = arrayToHash(components, (c) => c.id);
const hostsDictionary = arrayToHash(hosts, (h) => h.id);

describe('Cluster mapping utils', () => {
  test('test getHostsMapping empty mapping', () => {
    const filter: HostMappingFilter = { componentDisplayName: '' };
    const hostsMapping = getHostsMapping(hosts, emptyMapping, componentsDictionary, filter);

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
    const filter: HostMappingFilter = { componentDisplayName: '' };
    const hostsMapping = getHostsMapping(hosts, mapping, componentsDictionary, filter);

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
    const filter: ServiceMappingFilter = { hostName: '' };
    const servicesMapping = getServicesMapping(components, emptyMapping, hostsDictionary, filter);

    const expected: ServiceMapping[] = [
      {
        service: services[0],
        validationSummary: 'valid',
        componentsMapping: [
          {
            component: components[0],
            constraintsValidationResult: { isValid: true },
            filteredHosts: [],
            hosts: [],
            requireValidationResults: { isValid: true },
            validationSummary: 'valid',
          },
          {
            component: components[1],
            constraintsValidationResult: { isValid: true },
            filteredHosts: [],
            hosts: [],
            requireValidationResults: { isValid: true },
            validationSummary: 'valid',
          },
        ],
      },
      {
        service: services[1],
        validationSummary: 'valid',
        componentsMapping: [
          {
            component: components[2],
            constraintsValidationResult: { isValid: true },
            filteredHosts: [],
            hosts: [],
            requireValidationResults: { isValid: true },
            validationSummary: 'valid',
          },
        ],
      },
    ];

    expect(servicesMapping).toStrictEqual(expected);
  });

  test('test getServicesMapping mapping', () => {
    const filter: ServiceMappingFilter = { hostName: '' };
    const servicesMapping = getServicesMapping(components, mapping, hostsDictionary, filter);

    const expected: ServiceMapping[] = [
      {
        service: services[0],
        validationSummary: 'valid',
        componentsMapping: [
          {
            component: components[0],
            constraintsValidationResult: { isValid: true },
            filteredHosts: [hosts[0]],
            hosts: [hosts[0]],
            requireValidationResults: { isValid: true },
            validationSummary: 'valid',
          },
          {
            component: components[1],
            constraintsValidationResult: { isValid: true },
            filteredHosts: [hosts[0]],
            hosts: [hosts[0]],
            requireValidationResults: { isValid: true },
            validationSummary: 'valid',
          },
        ],
      },
      {
        service: services[1],
        validationSummary: 'valid',
        componentsMapping: [
          {
            component: components[2],
            constraintsValidationResult: { isValid: true },
            filteredHosts: [hosts[2]],
            hosts: [hosts[2]],
            requireValidationResults: { isValid: true },
            validationSummary: 'valid',
          },
        ],
      },
    ];

    expect(servicesMapping).toStrictEqual(expected);
  });

  test('test mapComponentsToHost', () => {
    const filter: HostMappingFilter = { componentDisplayName: '' };
    const hostsMapping = getHostsMapping(hosts, mapping, componentsDictionary, filter);
    const newMapping = mapComponentsToHost(hostsMapping, [components[0], components[1]], hosts[1]);

    const expected: AdcmMapping[] = [
      { hostId: 1, componentId: 1 },
      { hostId: 1, componentId: 2 },
      { hostId: 2, componentId: 1 },
      { hostId: 2, componentId: 2 },
      { hostId: 3, componentId: 3 },
    ];

    expect(newMapping).toEqual(expect.arrayContaining(expected));
  });

  test('test mapHostsToComponent', () => {
    const filter: ServiceMappingFilter = { hostName: '' };
    const servicesMapping = getServicesMapping(components, mapping, hostsDictionary, filter);
    const newMapping = mapHostsToComponent(servicesMapping, [hosts[1]], components[0]);

    const expected: AdcmMapping[] = [
      { hostId: 1, componentId: 2 },
      { hostId: 2, componentId: 1 },
      { hostId: 3, componentId: 3 },
    ];

    expect(newMapping).toEqual(expect.arrayContaining(expected));
  });

  test('test validateConstraint', () => {
    // Check all hosts constraint
    expect(validateConstraint(['+'], 2, 0)).toEqual({
      isValid: false,
      error: 'Component should be installed on all hosts of cluster.',
    });
    expect(validateConstraint(['+'], 2, 1)).toEqual({
      isValid: false,
      error: 'Component should be installed on all hosts of cluster.',
    });
    expect(validateConstraint(['+'], 2, 2)).toEqual({ isValid: true });

    // Check range constraint
    expect(validateConstraint([0, 1], 2, 0)).toEqual({ isValid: true });
    expect(validateConstraint([0, 1], 2, 1)).toEqual({ isValid: true });
    expect(validateConstraint([0, 1], 2, 2)).toEqual({
      isValid: false,
      error: 'Must be installed at least 0 and no more 1 components.',
    });
    expect(validateConstraint([3, 10], 5, 5)).toEqual({ isValid: true });

    expect(validateConstraint([0, '+'], 5, 0)).toEqual({ isValid: true });
    expect(validateConstraint([1, '+'], 5, 0)).toEqual({
      isValid: false,
      error: 'Must be installed at least 1 components.',
    });
    expect(validateConstraint([2, '+'], 5, 1)).toEqual({
      isValid: false,
      error: 'Must be installed at least 2 components.',
    });

    // Check exact contraint
    expect(validateConstraint([1], 2, 0)).toEqual({
      isValid: false,
      error: 'Exactly 1 component should be installed',
    });
    expect(validateConstraint([1], 2, 1)).toEqual({ isValid: true });
    expect(validateConstraint([2], 2, 2)).toEqual({ isValid: true });
    expect(validateConstraint([1], 2, 2)).toEqual({
      isValid: false,
      error: 'Exactly 1 component should be installed',
    });

    // Check odd constraint
    expect(validateConstraint(['odd'], 4, 3)).toEqual({ isValid: true });
    expect(validateConstraint([1, 'odd'], 4, 3)).toEqual({ isValid: true });
    expect(validateConstraint([1, 'odd'], 4, 2)).toEqual({
      isValid: false,
      error: 'Must be installed at least 1 components. Total amount should be odd.',
    });
  });
});
