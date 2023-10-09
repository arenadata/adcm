import React, { useState } from 'react';
import ConfigurationVersions from '../ConfigurationVersions/ConfigurationVersions';
import { AdcmConfigShortView, AdcmConfiguration } from '@models/adcm';
import { ConfigVersionAction, SelectVersionAction } from '../ConfigVersionPanel/ConfigVersionPanel.types';
import ConfigurationCompareDialog, {
  ConfigurationsCompareOptions,
} from '../ConfigurationCompareDialog/ConfigurationCompareDialog';

interface ConfigurationHeaderProps {
  configVersions: AdcmConfigShortView[];
  selectedConfigId: AdcmConfigShortView['id'] | null;
  setSelectedConfigId: (id: AdcmConfigShortView['id'] | null) => void;
  draftConfiguration: AdcmConfiguration | null;
  compareOptions: ConfigurationsCompareOptions;
}

const ConfigurationHeader: React.FC<ConfigurationHeaderProps> = ({
  draftConfiguration,
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
        leftConfigId={comparedConfigId ? selectedConfigId : null}
        rightConfigId={comparedConfigId}
        draftConfiguration={draftConfiguration}
        compareOptions={compareOptions}
        onClose={() => setComparedConfigId(null)}
      />
      <ConfigurationVersions
        selectedConfigId={selectedConfigId}
        isShowDraft={isShowDraft}
        onSelectAction={onSelectAction}
        {...props}
      />
    </>
  );
};
export default ConfigurationHeader;
