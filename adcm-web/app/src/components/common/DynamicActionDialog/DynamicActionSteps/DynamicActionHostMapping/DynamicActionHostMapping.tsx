import type React from 'react';
import { useMappingLayersV2 } from '@hooks';
import type { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';
import DynamicActionHostMappingLegacy from './DynamicActionHostMappingLegacy';
import DynamicActionHostMappingV2 from './DynamicActionHostMappingV2';

interface DynamicActionHostMappingProps {
  clusterId: number;
  actionDetails: AdcmDynamicActionDetails;
  configuration?: AdcmDynamicActionRunConfig['configuration'] | null;
  onNext: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

const DynamicActionHostMapping: React.FC<DynamicActionHostMappingProps> = (props) => {
  const [mappingLayersV2] = useMappingLayersV2();
  const Impl = mappingLayersV2 ? DynamicActionHostMappingV2 : DynamicActionHostMappingLegacy;
  return <Impl {...props} />;
};

export default DynamicActionHostMapping;
