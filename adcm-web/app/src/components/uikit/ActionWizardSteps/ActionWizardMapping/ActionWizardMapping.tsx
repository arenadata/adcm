import type React from 'react';
import { useMappingLayersV2 } from '@hooks';
import type { AdcmActionProcessMappingStep } from '@models/adcm/wizard';
import ActionWizardMappingLegacy from './ActionWizardMappingLegacy';
import ActionWizardMappingV2 from './ActionWizardMappingV2';

interface ActionWizardMappingProps {
  clusterId: number;
  step: AdcmActionProcessMappingStep;
  onSetIsValid: (isValid: boolean) => void;
  onClose: () => void;
  isReadOnly?: boolean;
}

const ActionWizardMapping: React.FC<ActionWizardMappingProps> = (props) => {
  const [mappingLayersV2] = useMappingLayersV2();
  const Impl = mappingLayersV2 ? ActionWizardMappingV2 : ActionWizardMappingLegacy;
  return <Impl {...props} />;
};

export default ActionWizardMapping;
