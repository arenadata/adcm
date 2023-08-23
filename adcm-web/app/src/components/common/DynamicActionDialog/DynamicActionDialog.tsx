import React, { ChangeEvent, useState } from 'react';
import { Checkbox, Dialog } from '@uikit';
import s from './DynamicActionDialog.module.scss';
import DynamicActionSteps from '@commonComponents/DynamicActionDialog/DynamicActionSteps/DynamicActionSteps';
import {
  getDefaultRunConfig,
  getDynamicActionTypes,
} from '@commonComponents/DynamicActionDialog/DynamicActionDialog.utils';
import { DynamicActionCommonOptions, DynamicActionType } from './DynamicAction.types';
import { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import DynamicActionConfirm from '@commonComponents/DynamicActionDialog/DynamicActionConfirm/DynamicActionConfirm';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';

interface DynamicActionDialogProps extends Omit<DynamicActionCommonOptions, 'onSubmit'> {
  clusterId: number;
  onSubmit: (data: AdcmDynamicActionRunConfig) => void;
}

const DynamicActionDialog: React.FC<DynamicActionDialogProps> = ({ clusterId, actionDetails, onCancel, onSubmit }) => {
  const [localActionRunConfig, setLocalActionRunConfig] = useState<AdcmDynamicActionRunConfig>(() => {
    return getDefaultRunConfig();
  });

  const handleCancel = () => {
    onCancel();
  };

  const handleSubmit = (data: Partial<AdcmDynamicActionRunConfig>) => {
    const newActionRunConfig = { ...localActionRunConfig, ...data };
    setLocalActionRunConfig(newActionRunConfig);
    onSubmit(newActionRunConfig);
  };

  const handleChangeVerbose = (event: ChangeEvent<HTMLInputElement>) => {
    const isVerbose = event.target.checked;
    setLocalActionRunConfig((prev) => ({ ...prev, isVerbose }));
  };

  const dynamicActionTypes = getDynamicActionTypes(actionDetails);

  const commonDialogOptions = {
    isOpen: true,
    title: `Run an action: ${actionDetails.displayName}`,
    onOpenChange: handleCancel,
    onCancel: handleCancel,
  };

  if (dynamicActionTypes.includes(DynamicActionType.Confirm)) {
    const dialogControls = (
      <CustomDialogControls actionButtonLabel="Run" onCancel={onCancel} onAction={() => onSubmit(localActionRunConfig)}>
        <Checkbox checked={localActionRunConfig.isVerbose} label="Verbose" onChange={handleChangeVerbose} />
      </CustomDialogControls>
    );

    return (
      <Dialog {...commonDialogOptions} dialogControls={dialogControls}>
        <DynamicActionConfirm actionDetails={actionDetails} />
      </Dialog>
    );
  }

  return (
    <Dialog {...commonDialogOptions} dialogControls={false}>
      <DynamicActionSteps
        actionSteps={dynamicActionTypes}
        clusterId={clusterId}
        actionDetails={actionDetails}
        onSubmit={handleSubmit}
        onCancel={onCancel}
      />
      <div className={s.dynamicActionDialog__verbose}>
        <Checkbox checked={localActionRunConfig.isVerbose} label="Verbose" onChange={handleChangeVerbose} />
      </div>
    </Dialog>
  );
};
export default DynamicActionDialog;
