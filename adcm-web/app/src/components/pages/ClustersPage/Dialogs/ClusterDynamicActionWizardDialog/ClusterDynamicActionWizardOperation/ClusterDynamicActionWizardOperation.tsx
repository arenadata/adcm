import { useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import { useRequestClusterDynamicActionWizardDialog } from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/useRequestClusterDynamicActionWizardDialog';
import ActionWizardOperation from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperation';

interface ClusterDynamicActionWizardOperationProps {
  step: AdcmActionProcessOperationStep;
}

const ClusterDynamicActionWizardOperation = ({ step }: ClusterDynamicActionWizardOperationProps) => {
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);

  useRequestClusterDynamicActionWizardDialog(step);

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

export default ClusterDynamicActionWizardOperation;
