import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import { DialogV2, LabeledField, Select } from '@uikit';
import type { AdcmConfigShortView, AdcmConfiguration, AdcmFullConfigurationInfo } from '@models/adcm';
import type { SelectOption } from '@uikit/Select/Select.types';
import CompareJson from '@uikit/CompareJson/CompareJson';
import cn from 'classnames';
import s from './ConfigurationCompareDialog.module.scss';
import type { JSONObject } from '@models/json';
import { getCompareView } from './CompareConfiguration.utils';
import { prepareDate, renderConfigContent, createConfigSelectItem } from './ConfigurationCompareDialog.helpers';
import { useStore } from '@hooks';

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
  configVersions: AdcmConfigShortView[];
}

const noDialogControl = <></>;

const ConfigurationCompareDialog: React.FC<ConfigurationCompareDialogProps> = ({
  onClose,
  leftConfigId,
  rightConfigId,
  draftConfiguration,
  configVersions,
  compareOptions: { leftConfiguration, rightConfiguration, getLeftConfig, getRightConfig },
}) => {
  const [localLeftConfigId, setLocalLeftConfigId] = useState<number | null>(null);
  const [localRightConfigId, setLocalRightConfigId] = useState<number | null>(null);
  const [leftViewData, setLeftViewData] = useState<JSONObject | null>(null);
  const [rightViewData, setRightViewData] = useState<JSONObject | null>(null);
  const isOpen = localLeftConfigId !== null && localRightConfigId !== null;

  const username = useStore((state) => state.auth.username);

  const draftFullConfigurationInfo = useMemo<AdcmFullConfigurationInfo | null>(() => {
    if (draftConfiguration === null) return null;

    return {
      id: 0,
      creationTime: '',
      description: '',
      createdBy: username,
      isCurrent: false,
      configuration: draftConfiguration,
    };
  }, [draftConfiguration, username]);

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

  useEffect(() => {
    if (localLeftConfiguration?.configuration) {
      const { schema, configurationData, attributes } = localLeftConfiguration.configuration;
      const compareView = getCompareView(schema, configurationData, attributes);
      setLeftViewData(compareView);
    }
  }, [setLeftViewData, localLeftConfiguration?.configuration]);

  useEffect(() => {
    if (localRightConfiguration?.configuration) {
      const { schema, configurationData, attributes } = localRightConfiguration.configuration;
      const compareView = getCompareView(schema, configurationData, attributes);
      setRightViewData(compareView);
    }
  }, [setRightViewData, localRightConfiguration?.configuration]);

  const ConfigSelectItem = useMemo(() => createConfigSelectItem(configVersions), [configVersions]);

  const configsOptions = useMemo(() => {
    const options: SelectOption<number>[] = configVersions.map((config) => {
      const date = prepareDate(config.creationTime);
      const description = config.description || String(config.id);
      return {
        value: config.id,
        label: `${date} - ${description}`,
        ItemComponent: ConfigSelectItem,
      };
    });

    if (draftFullConfigurationInfo !== null) {
      options.unshift({
        value: 0,
        label: 'now - Draft Configuration',
        ItemComponent: ConfigSelectItem,
      });
    }
    return options;
  }, [configVersions, draftFullConfigurationInfo, ConfigSelectItem]);

  const handleRenderConfigValue = (value: number | null) => {
    return renderConfigContent(value, configVersions);
  };

  if (!isOpen) return null;

  return (
    <DialogV2
      onCancel={onClose}
      dialogControls={noDialogControl}
      width="100%"
      height="100%"
      title="Compare configurations"
    >
      <div>
        <div className={s.configurationCompareDialog__toolbar}>
          <LabeledField label="Left Configuration">
            <Select
              options={configsOptions}
              value={localLeftConfigId}
              onChange={setLocalLeftConfigId}
              renderValue={handleRenderConfigValue}
            />
          </LabeledField>
          <LabeledField label="Right Configuration">
            <Select
              options={configsOptions}
              value={localRightConfigId}
              onChange={setLocalRightConfigId}
              renderValue={handleRenderConfigValue}
            />
          </LabeledField>
        </div>
        <div className={cn(s.configurationCompareDialog__body, 'scroll')}>
          {leftViewData && rightViewData && <CompareJson oldData={leftViewData} newData={rightViewData} />}
        </div>
      </div>
    </DialogV2>
  );
};

export default ConfigurationCompareDialog;
