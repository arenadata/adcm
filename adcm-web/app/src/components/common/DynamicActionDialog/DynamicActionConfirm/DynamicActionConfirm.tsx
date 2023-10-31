import React from 'react';
import { AdcmDynamicActionDetails } from '@models/adcm/dynamicAction';

interface DynamicActionConfirmProps {
  actionDetails: AdcmDynamicActionDetails;
}

const DynamicActionConfirm: React.FC<DynamicActionConfirmProps> = ({ actionDetails }) => {
  return (
    <div>
      <div>{actionDetails.disclaimer || `${actionDetails.displayName} will be started.`}</div>
    </div>
  );
};

export default DynamicActionConfirm;
