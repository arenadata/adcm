import { useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import ActionWizardOperation from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperation';
import { useEntityWizardDataContext } from '../EntityWizardContextProvider/EntityWizardData.context';
import { useRequestEntityDynamicActionWizardDialog } from '../hooks';

interface EntityDynamicActionWizardOperationProps {
  step: AdcmActionProcessOperationStep;
}

const EntityDynamicActionWizardOperation = ({ step }: EntityDynamicActionWizardOperationProps) => {
  const jobsData = useStore((s) => s.adcm.entityWizard.jobsData);

  const stepId = step.id;

  const { entityArgs, entityType } = useEntityWizardDataContext();
  useRequestEntityDynamicActionWizardDialog(entityType, entityArgs, step);

  if (!jobsData || !jobsData[stepId]) {
    return null;
  }

  const { job, subJobLog } = jobsData[stepId];

  if (!job || !subJobLog) {
    return null;
  }

  return <ActionWizardOperation job={job} subJobLog={subJobLog} />;
};

export default EntityDynamicActionWizardOperation;
