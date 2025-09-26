import { useStore } from '@hooks';
import type { AdcmActionProcessStep } from '@models/adcm/wizard';
import { useRequestClusterDynamicActionWizardDialog } from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/useRequestClusterDynamicActionWizardDialog';
import ActionWizardOperation from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperation';

interface ClusterDynamicActionWizardOperationProps {
  step: AdcmActionProcessStep;
}

const ClusterDynamicActionWizardOperation = ({ step }: ClusterDynamicActionWizardOperationProps) => {
  const job = useStore((s) => s.adcm.clustersWizard.job);
  const subJobLog = useStore((s) => s.adcm.clustersWizard.subJobLog);

  useRequestClusterDynamicActionWizardDialog();

  if (!job || !subJobLog) return null;

  return step && step.state !== 'created' && <ActionWizardOperation job={job} subJobLog={subJobLog} />;
};

export default ClusterDynamicActionWizardOperation;
