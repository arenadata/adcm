import React, { useState } from 'react';
import ConfigurationVersions from '../ConfigurationVersions/ConfigurationVersions';
import type { AdcmConfigShortView, AdcmConfiguration } from '@models/adcm';
import type { SelectVersionAction } from '../ConfigVersionPanel/ConfigVersionPanel.types';
import { ConfigVersionAction } from '../ConfigVersionPanel/ConfigVersionPanel.types';
import type { ConfigurationsCompareOptions } from '../ConfigurationCompareDialog/ConfigurationCompareDialog';
import ConfigurationCompareDialog from '../ConfigurationCompareDialog/ConfigurationCompareDialog';

interface ConfigurationHeaderProps {
  configVersions: AdcmConfigShortView[];
  selectedConfigId: AdcmConfigShortView['id'] | null;
  setSelectedConfigId: (id: AdcmConfigShortView['id'] | null) => void;
  draftConfiguration: AdcmConfiguration | null;
  compareOptions: ConfigurationsCompareOptions;
}

const ConfigurationHeader: React.FC<ConfigurationHeaderProps> = ({
  draftConfiguration,
  configVersions,
  selectedConfigId,
  compareOptions,
  ...props
}) => {
  const [comparedConfigId, setComparedConfigId] = useState<number | null>(null);

  const isShowDraft = draftConfiguration !== null;
  const onSelectAction = ({ action, configId }: SelectVersionAction) => {
    if (action === ConfigVersionAction.Compare) {
      setComparedConfigId(configId);
    }
  };

  return (
    <>
      <ConfigurationCompareDialog
        // when not set rightConfigId not need set leftConfigId
        leftConfigId={comparedConfigId !== null ? selectedConfigId : null}
        rightConfigId={comparedConfigId}
        draftConfiguration={draftConfiguration}
        compareOptions={compareOptions}
        onClose={() => setComparedConfigId(null)}
        configVersions={configVersions}
      />
      <ConfigurationVersions
        configVersions={configVersions}
        selectedConfigId={selectedConfigId}
        isShowDraft={isShowDraft}
        onSelectAction={onSelectAction}
        {...props}
      />
    </>
  );
};
export default ConfigurationHeader;
