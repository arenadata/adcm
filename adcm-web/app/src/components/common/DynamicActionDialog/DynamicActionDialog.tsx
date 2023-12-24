import React, { ChangeEvent, useState, useEffect, useMemo } from 'react';
import { Checkbox, Dialog } from '@uikit';
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
  clusterId: number | null;
  onSubmit: (data: AdcmDynamicActionRunConfig) => void;
}

const DynamicActionDialog: React.FC<DynamicActionDialogProps> = ({ clusterId, actionDetails, onCancel, onSubmit }) => {
  const [localActionRunConfig, setLocalActionRunConfig] = useState<AdcmDynamicActionRunConfig>(() => {
    return getDefaultRunConfig();
  });

  const dynamicActionTypes = useMemo(() => {
    return getDynamicActionTypes(actionDetails);
  }, [actionDetails]);
  const [isShowDisclaimer, setIsShowDisclaimer] = useState(dynamicActionTypes.includes(DynamicActionType.Confirm));

  useEffect(() => {
    setIsShowDisclaimer(dynamicActionTypes.includes(DynamicActionType.Confirm));
  }, [dynamicActionTypes, setIsShowDisclaimer]);

  const handleSubmit = (data: Partial<AdcmDynamicActionRunConfig>) => {
    const newActionRunConfig = { ...localActionRunConfig, ...data };
    setLocalActionRunConfig(newActionRunConfig);
    setIsShowDisclaimer(true);
  };

  const handleChangeVerbose = (event: ChangeEvent<HTMLInputElement>) => {
    const isVerbose = event.target.checked;
    setLocalActionRunConfig((prev) => ({ ...prev, isVerbose }));
  };

  const commonDialogOptions = {
    isOpen: true,
    title: `Run an action: ${actionDetails.displayName}`,
    onOpenChange: onCancel,
    onCancel: onCancel,
  };

  if (isShowDisclaimer) {
    const dialogControls = (
      <CustomDialogControls
        actionButtonLabel="Run"
        onCancel={onCancel}
        onAction={() => onSubmit(localActionRunConfig)}
        isActionButtonDefaultFocus={true}
      >
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
    <Dialog {...commonDialogOptions} dialogControls={false} width="100%" maxWidth="980px">
      <DynamicActionSteps
        actionSteps={dynamicActionTypes}
        clusterId={clusterId}
        actionDetails={actionDetails}
        onSubmit={handleSubmit}
        onCancel={onCancel}
      />
    </Dialog>
  );
};
export default DynamicActionDialog;
