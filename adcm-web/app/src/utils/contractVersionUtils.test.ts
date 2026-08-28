import { AdcmContractVersionStatus } from '@models/adcm/bundle';
import type { AdcmCluster, AdcmPrototype } from '@models/adcm';
import {
  attachContractVersionsToClusters,
  getContractVersionBadgeStatus,
  getUniqueClusterPrototypeIds,
  mergeClusterPreservingContractVersion,
} from './contractVersionUtils';

const makeCluster = (id: number, prototypeId: number, version = '1.0'): AdcmCluster =>
  ({
    id,
    name: `c${id}`,
    state: 'created',
    multiState: [],
    status: 'up',
    prototype: {
      id: prototypeId,
      name: 'product',
      displayName: 'Product',
      type: 'cluster',
      version,
    },
    description: '',
    concerns: [],
    isUpgradable: false,
    mainInfo: '',
  }) as AdcmCluster;

const makePrototype = (id: number, status: AdcmContractVersionStatus, value = '1.0'): AdcmPrototype =>
  ({
    id,
    bundle: {
      id,
      edition: 'community',
      contractVersion: { status, value },
    },
  }) as AdcmPrototype;

describe('contractVersionUtils', () => {
  test('getContractVersionBadgeStatus maps statuses', () => {
    expect(getContractVersionBadgeStatus(AdcmContractVersionStatus.Unsupported)).toBe('danger');
    expect(getContractVersionBadgeStatus(AdcmContractVersionStatus.Deprecated)).toBe('warning');
    expect(getContractVersionBadgeStatus(AdcmContractVersionStatus.Supported)).toBe('info');
    expect(getContractVersionBadgeStatus(undefined)).toBe('info');
  });

  test('getUniqueClusterPrototypeIds returns unique prototype ids', () => {
    expect(getUniqueClusterPrototypeIds([makeCluster(1, 10), makeCluster(2, 10), makeCluster(3, 20)])).toEqual([
      10, 20,
    ]);
  });

  test('attachContractVersionsToClusters maps contractVersion by prototype id', () => {
    const clusters = [makeCluster(1, 10), makeCluster(2, 10), makeCluster(3, 20)];
    const prototypes = [
      makePrototype(10, AdcmContractVersionStatus.Deprecated),
      makePrototype(20, AdcmContractVersionStatus.Unsupported, '0.9'),
    ];

    const result = attachContractVersionsToClusters(clusters, prototypes);

    expect(result[0].prototype.contractVersion?.status).toBe(AdcmContractVersionStatus.Deprecated);
    expect(result[1].prototype.contractVersion?.status).toBe(AdcmContractVersionStatus.Deprecated);
    expect(result[2].prototype.contractVersion?.status).toBe(AdcmContractVersionStatus.Unsupported);
  });

  test('attachContractVersionsToClusters leaves clusters unchanged when prototypes are empty', () => {
    const clusters = [makeCluster(1, 10)];
    const result = attachContractVersionsToClusters(clusters, []);
    expect(result[0].prototype.contractVersion).toBeUndefined();
  });

  test('mergeClusterPreservingContractVersion keeps previous contractVersion', () => {
    const existing = makeCluster(1, 10);
    existing.prototype.contractVersion = {
      status: AdcmContractVersionStatus.Unsupported,
      value: '0.9',
    };
    const incoming = makeCluster(1, 10);
    incoming.name = 'renamed';

    const merged = mergeClusterPreservingContractVersion(existing, incoming);
    expect(merged.name).toBe('renamed');
    expect(merged.prototype.contractVersion?.status).toBe(AdcmContractVersionStatus.Unsupported);
  });
});
