import type React from 'react';
import { useMemo } from 'react';
import { Dialog } from '@uikit';
import DynamicActionSteps from './DynamicActionSteps/DynamicActionSteps';
import { getDynamicActionSteps } from './DynamicActionDialog.utils';
import type { AdcmActionHostGroup, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';

export interface DynamicActionDialogProps {
  clusterId: number | null;
  actionDetails: AdcmDynamicActionDetails;
  actionHostGroup?: AdcmActionHostGroup;
  onSubmit: (data: AdcmDynamicActionRunConfig) => void;
  onCancel: () => void;
}

const DynamicActionDialog: React.FC<DynamicActionDialogProps> = ({
  clusterId,
  actionDetails,
  actionHostGroup,
  onCancel,
  onSubmit,
}) => {
  const dynamicActionTypes = useMemo(() => {
    return getDynamicActionSteps(actionDetails, actionHostGroup);
  }, [actionDetails, actionHostGroup]);

  const commonDialogOptions = {
    isOpen: true,
    title: `Run an action: ${actionDetails.displayName}`,
    onOpenChange: onCancel,
    onCancel: onCancel,
  };

  return (
    <Dialog {...commonDialogOptions} dialogControls={false} width="100%" maxWidth="980px">
      <DynamicActionSteps
        actionSteps={dynamicActionTypes}
        clusterId={clusterId}
        actionDetails={actionDetails}
        actionHostGroup={actionHostGroup}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    </Dialog>
  );
};
export default DynamicActionDialog;
