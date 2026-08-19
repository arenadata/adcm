import type React from 'react';
import { useMemo } from 'react';
import { DialogV2 } from '@uikit';
import DynamicActionSteps from './DynamicActionSteps/DynamicActionSteps';
import { getDynamicActionSteps } from './DynamicActionDialog.utils';
import type { AdcmActionHostGroup, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';

export interface DynamicActionDialogProps {
  clusterId: number | null;
  actionDetails: AdcmDynamicActionDetails;
  actionHostGroup?: AdcmActionHostGroup;
  onSubmit: (data: AdcmDynamicActionRunConfig) => void;
  onCancel: () => void;
  isConcernControlShown?: boolean;
}

const DynamicActionDialog: React.FC<DynamicActionDialogProps> = ({
  clusterId,
  actionDetails,
  actionHostGroup,
  onCancel,
  onSubmit,
  isConcernControlShown = true,
}) => {
  const dynamicActionTypes = useMemo(() => {
    return getDynamicActionSteps(actionDetails, actionHostGroup);
  }, [actionDetails, actionHostGroup]);

  const commonDialogOptions = {
    title: `Run an action: ${actionDetails.displayName}`,
    onCancel: onCancel,
  };

  return (
    <DialogV2
      {...commonDialogOptions}
      dialogControls={false}
      isNeedConfirmationOnCancel={true}
      width="100%"
      maxWidth="980px"
    >
      <DynamicActionSteps
        actionSteps={dynamicActionTypes}
        clusterId={clusterId}
        actionDetails={actionDetails}
        actionHostGroup={actionHostGroup}
        onSubmit={onSubmit}
        isConcernControlShown={isConcernControlShown}
      />
    </DialogV2>
  );
};
export default DynamicActionDialog;
