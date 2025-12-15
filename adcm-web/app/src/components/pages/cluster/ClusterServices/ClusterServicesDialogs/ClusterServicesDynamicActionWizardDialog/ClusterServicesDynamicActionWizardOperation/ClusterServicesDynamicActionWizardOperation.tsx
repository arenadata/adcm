import { useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import ActionWizardOperation from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperation';
import { useRequestClusterServicesDynamicActionWizardDialog } from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServicesDynamicActionWizardDialog/useRequestClusterServicesDynamicActionWizardDialog';

interface ClusterHostsDynamicActionWizardOperationProps {
  step: AdcmActionProcessOperationStep;
}

const ClusterServicesDynamicActionWizardOperation = ({ step }: ClusterHostsDynamicActionWizardOperationProps) => {
  const jobsData = useStore((s) => s.adcm.clusterServicesWizard.jobsData);

  useRequestClusterServicesDynamicActionWizardDialog(step);

  const stepId = step.id;

  if (!jobsData || !jobsData[stepId]) {
    return null;
  }

  const { job, subJobLog } = jobsData[stepId];

  if (!job || !subJobLog) {
    return null;
  }

  return <ActionWizardOperation job={job} subJobLog={subJobLog} />;
};

export default ClusterServicesDynamicActionWizardOperation;
