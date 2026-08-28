import type { ReactNode } from 'react';
import cn from 'classnames';
import { WarningMessage } from '@uikit';
import { AdcmContractVersionStatus, type AdcmCluster } from '@models/adcm';
import s from './ClusterContractVersionWarning.module.scss';

enum ClusterContractVersionWarningVariant {
  Warning = 'warning',
  Error = 'error',
}

interface ClusterContractVersionWarningProps {
  cluster?: AdcmCluster | null;
  className?: string;
}

const getWarning = (
  cluster: AdcmCluster,
): {
  variant: ClusterContractVersionWarningVariant;
  message: ReactNode;
} | null => {
  const version = <span className={s.version}>{cluster.prototype.version}</span>;

  switch (cluster.prototype.contractVersion?.status) {
    case AdcmContractVersionStatus.Unsupported:
      return {
        variant: ClusterContractVersionWarningVariant.Error,
        message: <>{version} version is not supported. To upgrade ADCM, you must upgrade the cluster</>,
      };
    case AdcmContractVersionStatus.Deprecated:
      return {
        variant: ClusterContractVersionWarningVariant.Warning,
        message: (
          <>
            {version} is deprecated and will not be supported in upcoming versions of ADCM. To upgrade ADCM in the
            future, you must upgrade the cluster
          </>
        ),
      };
    default:
      return null;
  }
};

const ClusterContractVersionWarning = ({ cluster, className }: ClusterContractVersionWarningProps) => {
  if (!cluster) {
    return null;
  }

  const warning = getWarning(cluster);
  if (!warning) {
    return null;
  }

  return (
    <WarningMessage variant={warning.variant} className={cn(s.contractVersionWarning, className)}>
      {warning.message}
    </WarningMessage>
  );
};

export default ClusterContractVersionWarning;
