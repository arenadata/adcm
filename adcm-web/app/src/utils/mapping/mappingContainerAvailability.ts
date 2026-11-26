import type { AdcmHostShortView, AdcmMappingComponent, ComponentId, HostId } from '@models/adcm';
import type { ComponentHostRelations } from './mapping.types';
import {
  firstDenyReason,
  getComponentLevelMapDeny,
  getHostMapBlockedReason,
  getPairRelation,
} from './componentHostRelations';

export type ItemAvailability = {
  disabled: boolean;
  title?: string;
};

export type ComponentContainerAvailability = {
  notAvailableError?: string;
  addError?: string;
  hostOptions: Record<HostId, ItemAvailability>;
  mappedHostDelete: Record<HostId, ItemAvailability>;
};

export type HostContainerAvailability = {
  addError?: string;
  componentOptions: Record<ComponentId, ItemAvailability>;
  mappedComponentDelete: Record<ComponentId, ItemAvailability>;
};

const buildOption = (isMapped: boolean, allowMapError?: string, allowUnmapError?: string): ItemAvailability => {
  const enabled = (allowMapError === undefined && !isMapped) || (allowUnmapError === undefined && isMapped);
  return {
    disabled: !enabled,
    title: enabled ? undefined : (allowMapError ?? allowUnmapError),
  };
};

export const buildComponentContainerAvailabilityFromRelations = (
  relations: ComponentHostRelations,
  componentId: ComponentId,
  allHosts: AdcmHostShortView[],
  mappedHostIds: Set<HostId>,
): ComponentContainerAvailability => {
  const notAvailableError = getComponentLevelMapDeny(relations, componentId);
  const hostOptions: Record<HostId, ItemAvailability> = {};
  const mappedHostDelete: Record<HostId, ItemAvailability> = {};

  for (const host of allHosts) {
    const pair = getPairRelation(relations, componentId, host.id);
    const allowMapError = firstDenyReason(pair.map.denyReasons);
    const allowUnmapError = firstDenyReason(pair.unmap.denyReasons);
    const isMapped = mappedHostIds.has(host.id);
    hostOptions[host.id] = buildOption(isMapped, allowMapError, allowUnmapError);
    if (isMapped) {
      mappedHostDelete[host.id] = {
        disabled: allowUnmapError !== undefined,
        title: allowUnmapError,
      };
    }
  }

  const hasEnabledOption = allHosts.some((host) => !hostOptions[host.id].disabled);
  const addError =
    notAvailableError ??
    (!hasEnabledOption
      ? allHosts.map((host) => hostOptions[host.id].title).find((title) => title !== undefined)
      : undefined);

  return { notAvailableError, addError, hostOptions, mappedHostDelete };
};

export const buildHostContainerAvailabilityFromRelations = (
  relations: ComponentHostRelations,
  hostId: HostId,
  allComponents: AdcmMappingComponent[],
  mappedComponentIds: Set<ComponentId>,
): HostContainerAvailability => {
  const componentOptions: Record<ComponentId, ItemAvailability> = {};
  const mappedComponentDelete: Record<ComponentId, ItemAvailability> = {};

  for (const component of allComponents) {
    const pair = getPairRelation(relations, component.id, hostId);
    const allowMapError = firstDenyReason(pair.map.denyReasons);
    const allowUnmapError = firstDenyReason(pair.unmap.denyReasons);
    const isMapped = mappedComponentIds.has(component.id);
    componentOptions[component.id] = buildOption(isMapped, allowMapError, allowUnmapError);
    if (isMapped) {
      mappedComponentDelete[component.id] = {
        disabled: allowUnmapError !== undefined,
        title: allowUnmapError,
      };
    }
  }

  const addError = getHostMapBlockedReason(
    relations,
    hostId,
    allComponents.map((component) => component.id),
    mappedComponentIds.size,
  );

  return { addError, componentOptions, mappedComponentDelete };
};
