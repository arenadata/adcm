import type { ReactNode } from 'react';
import { useStore } from '@hooks';
import { WarningMessage } from '@uikit';
import { AdcmContractVersionStatus, AdcmPrototypeType, type AdcmBundle } from '@models/adcm';
import s from './BundleOverviewContractVersionWarning.module.scss';

const getObjectName = (prototypeType?: AdcmPrototypeType) =>
  prototypeType === AdcmPrototypeType.Provider ? 'hostprovider' : 'cluster';

const getContractVersionWarning = (bundle: AdcmBundle): { variant: 'warning' | 'error'; message: ReactNode } | null => {
  const objectName = getObjectName(bundle.mainPrototype.type);

  switch (bundle.contractVersion?.status) {
    case AdcmContractVersionStatus.Unsupported:
      return {
        variant: 'error',
        message: (
          <>
            <strong>Warning</strong> {bundle.version} version is not supported, and you cannot create a {objectName}{' '}
            based on this bundle
          </>
        ),
      };
    case AdcmContractVersionStatus.Deprecated:
      return {
        variant: 'warning',
        message: (
          <>
            <strong>Warning</strong> {bundle.version} is deprecated and will not be supported in upcoming versions of
            ADCM. To upgrade ADCM in the future, you must upgrade the {objectName}
          </>
        ),
      };
    default:
      return null;
  }
};

const BundleOverviewContractVersionWarning = () => {
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);

  if (!bundle) {
    return null;
  }

  const warning = getContractVersionWarning(bundle);

  if (!warning) {
    return null;
  }

  return (
    <WarningMessage variant={warning.variant} className={s.contractVersionWarning}>
      {warning.message}
    </WarningMessage>
  );
};

export default BundleOverviewContractVersionWarning;
