import { useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import ActionWizardOperation from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperation';
import { useRequestServiceComponentsDynamicActionWizardDialog } from '@pages/cluster/service/ServiceComponents/Dialogs/ServiceComponentsDynamicActionWizardDialog/useRequestServiceComponentsDynamicActionWizardDialog';

interface ClusterHostsDynamicActionWizardOperationProps {
  step: AdcmActionProcessOperationStep;
}

const ServiceComponentsDynamicActionWizardOperation = ({ step }: ClusterHostsDynamicActionWizardOperationProps) => {
  const jobsData = useStore((s) => s.adcm.clusterServiceComponentsWizard.jobsData);

  useRequestServiceComponentsDynamicActionWizardDialog(step);

  const stepId = step.id;

  if (!jobsData || !jobsData[stepId]) {
    return null;
  }

  const { job, subJobLog, executionPlan } = jobsData[stepId];

  if (!job || !subJobLog) {
    return null;
  }

  return <ActionWizardOperation job={job} subJobLog={subJobLog} executionPlan={executionPlan} />;
};

export default ServiceComponentsDynamicActionWizardOperation;
