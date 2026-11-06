import type { AdcmMappingComponent } from '@models/adcm';
import { sortBy } from '@utils/arrayUtils';
import { isComponentEditable } from './mappingAvailability';
import type {
  MappingAvailability,
  MappingLayoutKind,
  MappingModel,
  MappingSortKind,
  MappingViewModel,
} from './mapping.types';
import type { SortDirection } from '@models/table';

export type LayoutOptions = {
  kind: MappingLayoutKind;
  sort: MappingSortKind;
  sortDirection?: SortDirection;
};

export const componentsMappingSortByName = (a: AdcmMappingComponent, b: AdcmMappingComponent) =>
  a.displayName.localeCompare(b.displayName);

const unknownComponentAvailability = {
  canMap: false,
  canUnmap: false,
  notAvailableReason: 'Unknown component',
};

export const layoutMappingViewModel = (
  model: MappingModel,
  availability: MappingAvailability,
  options: LayoutOptions,
): MappingViewModel => {
  const sortDirection = options.sortDirection ?? 'asc';

  if (options.kind === 'flat') {
    let components = model.componentsMapping.map((componentMapping) => ({
      ...componentMapping,
      availability: availability.components[componentMapping.component.id] ?? unknownComponentAvailability,
    }));

    if (options.sort === 'editableFirst') {
      components = sortBy(components, [
        (left, right) => {
          const leftAvailable = left.availability.notAvailableReason ? 0 : 1;
          const rightAvailable = right.availability.notAvailableReason ? 0 : 1;
          const leftEditable = isComponentEditable(left.availability) ? 1 : 0;
          const rightEditable = isComponentEditable(right.availability) ? 1 : 0;
          return rightEditable - leftEditable || rightAvailable - leftAvailable;
        },
        (left, right) => componentsMappingSortByName(left.component, right.component),
      ]);
    } else {
      components = sortBy(components, [(left, right) => componentsMappingSortByName(left.component, right.component)]);
    }

    if (sortDirection === 'desc') {
      components.reverse();
    }

    return { kind: 'flat', components };
  }

  if (options.kind === 'hosts') {
    let hosts = model.hostsMapping.map((hostMapping) => ({
      ...hostMapping,
      isEditable: Boolean(
        availability.hosts[hostMapping.host.id]?.canMap || availability.hosts[hostMapping.host.id]?.canUnmap,
      ),
    }));

    if (options.sort === 'editableFirst') {
      hosts = sortBy(hosts, [
        (left, right) => Number(right.isEditable) - Number(left.isEditable),
        (left, right) => left.host.name.localeCompare(right.host.name),
      ]);
    } else {
      hosts = sortBy(hosts, [(left, right) => left.host.name.localeCompare(right.host.name)]);
      hosts.forEach((hostMapping) => {
        hostMapping.components = [...hostMapping.components].sort((left, right) =>
          componentsMappingSortByName(left, right),
        );
      });
    }

    if (sortDirection === 'desc') {
      hosts.reverse();
    }

    return { kind: 'hosts', hosts };
  }

  let services = model.servicesMapping.map((serviceMapping) => ({
    ...serviceMapping,
    isEditable: availability.services[serviceMapping.service.id]?.isEditable ?? false,
    componentsMapping: serviceMapping.componentsMapping.map((componentMapping) => ({
      ...componentMapping,
      availability: availability.components[componentMapping.component.id] ?? unknownComponentAvailability,
    })),
  }));

  if (options.sort === 'editableFirst') {
    services = sortBy(services, [
      (left, right) => Number(right.isEditable) - Number(left.isEditable),
      (left, right) => left.service.displayName.localeCompare(right.service.displayName),
    ]);
    services.forEach((serviceMapping) => {
      serviceMapping.componentsMapping = sortBy(serviceMapping.componentsMapping, [
        (left, right) => {
          const leftAvailable = left.availability.notAvailableReason ? 0 : 1;
          const rightAvailable = right.availability.notAvailableReason ? 0 : 1;
          const leftEditable = isComponentEditable(left.availability) ? 1 : 0;
          const rightEditable = isComponentEditable(right.availability) ? 1 : 0;
          return rightEditable - leftEditable || rightAvailable - leftAvailable;
        },
        (left, right) => componentsMappingSortByName(left.component, right.component),
      ]);
    });
  } else {
    services = sortBy(services, [(left, right) => left.service.displayName.localeCompare(right.service.displayName)]);
    services.forEach((serviceMapping) => {
      serviceMapping.componentsMapping = sortBy(serviceMapping.componentsMapping, [
        (left, right) => componentsMappingSortByName(left.component, right.component),
      ]);
    });
  }

  if (sortDirection === 'desc') {
    services.reverse();
  }

  return { kind: 'services', services };
};
