import { useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import ActionWizardOperation from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperation';
import { useRequestClusterHostsDynamicActionWizardDialog } from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/ClusterHostsDynamicActionWizardDialog/useRequestClusterHostsDynamicActionWizardDialog';

interface ClusterHostsDynamicActionWizardOperationProps {
  step: AdcmActionProcessOperationStep;
}

const ClusterHostsDynamicActionWizardOperation = ({ step }: ClusterHostsDynamicActionWizardOperationProps) => {
  const jobsData = useStore((s) => s.adcm.clusterHostsWizard.jobsData);

  useRequestClusterHostsDynamicActionWizardDialog(step);

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

export default ClusterHostsDynamicActionWizardOperation;
