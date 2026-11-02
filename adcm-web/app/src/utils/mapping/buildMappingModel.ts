import type {
  AdcmHostShortView,
  AdcmMapping,
  AdcmMappingComponent,
  ComponentId,
  HostId,
  ServiceId,
} from '@models/adcm';
import { arrayToHash } from '@utils/arrayUtils';
import type { ComponentMapping, HostMapping, MappingModel, ServiceMapping } from './mapping.types';

const projectComponentsMapping = (
  pairs: AdcmMapping[],
  components: AdcmMappingComponent[],
  hostsById: Record<HostId, AdcmHostShortView>,
): { componentsMapping: ComponentMapping[]; unmappedHostsId: number[] } => {
  const componentHostsDictionary: Record<ComponentId, AdcmHostShortView[]> = {};
  const unmappedHostsId: number[] = [];

  for (const pair of pairs) {
    componentHostsDictionary[pair.componentId] = componentHostsDictionary[pair.componentId] ?? [];
    const host = hostsById[pair.hostId];
    if (host) {
      componentHostsDictionary[pair.componentId].push(host);
    } else {
      unmappedHostsId.push(pair.hostId);
    }
  }

  return {
    componentsMapping: components.map((component) => ({
      component,
      hosts: componentHostsDictionary[component.id] ?? [],
    })),
    unmappedHostsId,
  };
};

const projectHostsMapping = (
  pairs: AdcmMapping[],
  hosts: AdcmHostShortView[],
  componentsById: Record<ComponentId, AdcmMappingComponent>,
): HostMapping[] => {
  const hostComponentsDictionary: Record<HostId, AdcmMappingComponent[]> = {};

  for (const pair of pairs) {
    hostComponentsDictionary[pair.hostId] = hostComponentsDictionary[pair.hostId] ?? [];
    const component = componentsById[pair.componentId];
    if (component) {
      hostComponentsDictionary[pair.hostId].push(component);
    }
  }

  return hosts.map((host) => ({
    host,
    components: hostComponentsDictionary[host.id] ?? [],
  }));
};

const projectServicesMapping = (componentsMapping: ComponentMapping[]): ServiceMapping[] => {
  const servicesDictionary: Record<ServiceId, ComponentMapping['component']['service']> = {};
  const serviceComponentsDictionary: Record<ServiceId, ComponentMapping[]> = {};

  for (const componentMapping of componentsMapping) {
    const service = componentMapping.component.service;
    servicesDictionary[service.id] = service;
    serviceComponentsDictionary[service.id] = serviceComponentsDictionary[service.id] ?? [];
    serviceComponentsDictionary[service.id].push(componentMapping);
  }

  return Object.values(servicesDictionary).map((service) => ({
    service,
    componentsMapping: serviceComponentsDictionary[service.id] ?? [],
  }));
};

export const buildMappingModel = (
  pairs: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
): MappingModel => {
  const hostsById = arrayToHash(hosts, (host) => host.id);
  const componentsById = arrayToHash(components, (component) => component.id);
  const { componentsMapping, unmappedHostsId } = projectComponentsMapping(pairs, components, hostsById);
  const hostsMapping = projectHostsMapping(pairs, hosts, componentsById);
  const servicesMapping = projectServicesMapping(componentsMapping);

  return {
    componentsMapping,
    hostsMapping,
    servicesMapping,
    unmappedHostsId,
  };
};
