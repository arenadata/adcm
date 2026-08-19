import { AdcmContractVersionStatus } from '@models/adcm/bundle';
import type { AdcmPrototypeVersions } from '@models/adcm';

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
