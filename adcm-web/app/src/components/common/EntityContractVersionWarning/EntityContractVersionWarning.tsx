import type { ReactNode } from 'react';
import cn from 'classnames';
import { WarningMessage } from '@uikit';
import { AdcmContractVersionStatus, type AdcmCluster, type AdcmHostProvider } from '@models/adcm';
import s from './EntityContractVersionWarning.module.scss';

enum EntityContractVersionWarningVariant {
  Warning = 'warning',
  Error = 'error',
}

type EntityType = 'cluster' | 'hostprovider';

interface EntityContractVersionWarningProps {
  entity?: AdcmCluster | AdcmHostProvider | null;
  entityType: EntityType;
  className?: string;
}

const getWarning = (
  entity: AdcmCluster | AdcmHostProvider,
  entityType: EntityType,
): {
  variant: EntityContractVersionWarningVariant;
  message: ReactNode;
} | null => {
  const version = <span className={s.version}>{entity.prototype.version}</span>;

  switch (entity.prototype.contractVersion?.status) {
    case AdcmContractVersionStatus.Unsupported:
      return {
        variant: EntityContractVersionWarningVariant.Error,
        message: (
          <>
            {version} version is not supported. To upgrade ADCM, you must upgrade the {entityType}
          </>
        ),
      };
    case AdcmContractVersionStatus.Deprecated:
      return {
        variant: EntityContractVersionWarningVariant.Warning,
        message: (
          <>
            {version} is deprecated and will not be supported in upcoming versions of ADCM. To upgrade ADCM in the
            future, you must upgrade the {entityType}
          </>
        ),
      };
    default:
      return null;
  }
};

const EntityContractVersionWarning = ({ entity, entityType, className }: EntityContractVersionWarningProps) => {
  if (!entity) {
    return null;
  }

  const warning = getWarning(entity, entityType);
  if (!warning) {
    return null;
  }

  return (
    <WarningMessage variant={warning.variant} className={cn(s.contractVersionWarning, className)}>
      {warning.message}
    </WarningMessage>
  );
};

export default EntityContractVersionWarning;
