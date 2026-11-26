import { AdcmContractVersionStatus, type AdcmContractVersion } from '@models/adcm/bundle';
import type { AdcmCluster, AdcmHostProvider, AdcmPrototype, AdcmPrototypeVersions } from '@models/adcm';
import type { BadgeStatus } from '@uikit/Badge/Badge.types';

export const contractVersionBadgeStatuses: Record<AdcmContractVersionStatus, BadgeStatus> = {
  [AdcmContractVersionStatus.Unsupported]: 'danger',
  [AdcmContractVersionStatus.Deprecated]: 'warning',
  [AdcmContractVersionStatus.Supported]: 'info',
};

export const getContractVersionBadgeStatus = (status?: AdcmContractVersionStatus): BadgeStatus =>
  status ? contractVersionBadgeStatuses[status] : contractVersionBadgeStatuses[AdcmContractVersionStatus.Supported];

export const getUniqueEntityPrototypeIds = (entities: (AdcmCluster | AdcmHostProvider)[]): number[] => [
  ...new Set(entities.map((entity) => entity.prototype.id)),
];

export const attachContractVersionsToEntities = (
  entities: (AdcmCluster | AdcmHostProvider)[],
  prototypes: AdcmPrototype[],
): (AdcmCluster | AdcmHostProvider)[] => {
  if (!entities.length || !prototypes.length) {
    return entities;
  }

  const contractVersionByPrototypeId = new Map<number, AdcmContractVersion>();
  for (const prototype of prototypes) {
    if (prototype.bundle?.contractVersion) {
      contractVersionByPrototypeId.set(prototype.id, prototype.bundle.contractVersion);
    }
  }

  return entities.map((entity) => {
    const contractVersion = contractVersionByPrototypeId.get(entity.prototype.id);
    if (!contractVersion) {
      return entity;
    }
    return {
      ...entity,
      prototype: {
        ...entity.prototype,
        contractVersion,
      },
    };
  });
};

export const mergeClusterPreservingContractVersion = (
  existing: AdcmCluster | undefined,
  incoming: AdcmCluster,
): AdcmCluster => ({
  ...incoming,
  prototype: {
    ...incoming.prototype,
    contractVersion: incoming.prototype.contractVersion ?? existing?.prototype.contractVersion,
  },
});

export const excludeUnsupportedPrototypeVersions = (
  prototypeVersions: AdcmPrototypeVersions[],
): AdcmPrototypeVersions[] => {
  const result: AdcmPrototypeVersions[] = [];

  for (const item of prototypeVersions) {
    const versions = item.versions.filter(
      ({ bundle }) => bundle.contractVersion?.status !== AdcmContractVersionStatus.Unsupported,
    );

    if (versions.length === 0) {
      continue;
    }

    result.push(versions.length === item.versions.length ? item : { ...item, versions });
  }

  return result;
};
