import React, { useEffect, useMemo, useState } from 'react';
import { Dialog } from '@uikit';
import { AdcmConfigShortView, AdcmConfiguration, AdcmFullConfigurationInfo } from '@models/adcm';

export type ConfigurationsCompareOptions = {
  leftConfiguration: AdcmFullConfigurationInfo | null;
  rightConfiguration: AdcmFullConfigurationInfo | null;
  getLeftConfig: (id: AdcmConfigShortView['id']) => void;
  getRightConfig: (id: AdcmConfigShortView['id']) => void;
};

interface ConfigurationCompareDialogProps {
  leftConfigId: number | null;
  rightConfigId: number | null;
  compareOptions: ConfigurationsCompareOptions;
  draftConfiguration: AdcmConfiguration | null;
  onClose: () => void;
}

const ConfigurationCompareDialog: React.FC<ConfigurationCompareDialogProps> = ({
  onClose,
  leftConfigId,
  rightConfigId,
  draftConfiguration,
  compareOptions: { leftConfiguration, rightConfiguration, getLeftConfig, getRightConfig },
}) => {
  const [localLeftConfigId, setLocalLeftConfigId] = useState<number | null>(null);
  const [localRightConfigId, setLocalRightConfigId] = useState<number | null>(null);
  const isOpen = localLeftConfigId !== null && localRightConfigId !== null;

  const draftFullConfigurationInfo = useMemo<AdcmFullConfigurationInfo | null>(() => {
    if (draftConfiguration === null) return null;

    return {
      id: 0,
      creationTime: '',
      description: '',
      isCurrent: false,
      configuration: draftConfiguration,
    };
  }, [draftConfiguration]);

  const localLeftConfiguration = localLeftConfigId === 0 ? draftFullConfigurationInfo : leftConfiguration;
  const localRightConfiguration = localRightConfigId === 0 ? draftFullConfigurationInfo : rightConfiguration;

  useEffect(() => {
    setLocalLeftConfigId(leftConfigId);
    setLocalRightConfigId(rightConfigId);
  }, [leftConfigId, rightConfigId, setLocalLeftConfigId, setLocalRightConfigId]);

  useEffect(() => {
    localLeftConfigId && getLeftConfig(localLeftConfigId);
  }, [localLeftConfigId, getLeftConfig]);

  useEffect(() => {
    localRightConfigId && getRightConfig(localRightConfigId);
  }, [localRightConfigId, getRightConfig]);

  const noDialogControl = <></>;
  return (
    <Dialog isOpen={isOpen} onOpenChange={onClose} dialogControls={noDialogControl} width="100%" height="100%">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', wordBreak: 'break-all' }}>
        <div>{JSON.stringify(localLeftConfiguration?.configuration?.configurationData)}</div>
        <div>{JSON.stringify(localRightConfiguration?.configuration?.configurationData)}</div>
      </div>
      Compare versions {leftConfigId} and {rightConfigId}
    </Dialog>
  );
};

export default ConfigurationCompareDialog;
