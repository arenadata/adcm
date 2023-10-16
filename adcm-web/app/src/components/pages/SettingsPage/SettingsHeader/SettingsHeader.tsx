import React from 'react';
import { BaseStatus, Statusable } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import SettingsDynamicActionsIcon from './SettingsDynamicActionsIcon/SettingsDynamicActionsIcon';
import Concern from '@commonComponents/Concern/Concern';

const SettingsHeader: React.FC = () => {
  return (
    <EntityHeader
      title={
        <Statusable status={'unknown' as BaseStatus}>
          <SettingsDynamicActionsIcon />
          <Concern concerns={[]} />
          ADCM
        </Statusable>
      }
    />
  );
};

export default SettingsHeader;
