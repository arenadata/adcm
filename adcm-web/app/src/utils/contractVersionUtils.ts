import { AdcmContractVersionStatus, type AdcmContractVersion } from '@models/adcm/bundle';
import type { AdcmCluster, AdcmPrototype, AdcmPrototypeVersions } from '@models/adcm';
import type { BadgeStatus } from '@uikit/Badge/Badge.types';

export const contractVersionBadgeStatuses: Record<AdcmContractVersionStatus, BadgeStatus> = {
  [AdcmContractVersionStatus.Unsupported]: 'danger',
  [AdcmContractVersionStatus.Deprecated]: 'warning',
  [AdcmContractVersionStatus.Supported]: 'info',
};

export const getContractVersionBadgeStatus = (status?: AdcmContractVersionStatus): BadgeStatus =>
  status ? contractVersionBadgeStatuses[status] : contractVersionBadgeStatuses[AdcmContractVersionStatus.Supported];

export const getUniqueClusterPrototypeIds = (clusters: AdcmCluster[]): number[] => [
  ...new Set(clusters.map((cluster) => cluster.prototype.id)),
];

export const attachContractVersionsToClusters = (
  clusters: AdcmCluster[],
  prototypes: AdcmPrototype[],
): AdcmCluster[] => {
  if (!clusters.length || !prototypes.length) {
    return clusters;
  }

  const contractVersionByPrototypeId = new Map<number, AdcmContractVersion>();
  for (const prototype of prototypes) {
    if (prototype.bundle?.contractVersion) {
      contractVersionByPrototypeId.set(prototype.id, prototype.bundle.contractVersion);
    }
  }

  return clusters.map((cluster) => {
    const contractVersion = contractVersionByPrototypeId.get(cluster.prototype.id);
    if (!contractVersion) {
      return cluster;
    }
    return {
      ...cluster,
      prototype: {
        ...cluster.prototype,
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
