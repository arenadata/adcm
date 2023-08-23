import React from 'react';
import { AdcmDynamicActionDetails } from '@models/adcm/dynamicAction';

interface DynamicActionConfirmProps {
  actionDetails: AdcmDynamicActionDetails;
}

const DynamicActionConfirm: React.FC<DynamicActionConfirmProps> = ({ actionDetails }) => {
  return (
    <div>
      <div>{actionDetails.disclaimer || `You will run ${actionDetails.displayName} action. Are you sure?`}</div>
    </div>
  );
};

export default DynamicActionConfirm;
