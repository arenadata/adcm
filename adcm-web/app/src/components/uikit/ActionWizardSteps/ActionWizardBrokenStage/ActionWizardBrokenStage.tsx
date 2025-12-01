import type React from 'react';
import s from './ActionWizardBrokenStage.module.scss';
import { Link } from 'react-router-dom';
import { Button, Icon } from '@uikit';
import { useClipboardCopy } from '@hooks';
import { HelperLinkActions } from '@constants';

export interface getBrokenStepPayload {
  entityId: number;
  actionId: number;
  processId: number;
  stepId: number;
}

interface ActionWizardBrokenStageProps {
  brokenStepError: string;
  onClose: () => void;
}

const ActionWizardBrokenStage: React.FC<ActionWizardBrokenStageProps> = ({
  brokenStepError,
  onClose,
}: ActionWizardBrokenStageProps) => {
  const [_, copyToClipboard] = useClipboardCopy();

  const handleCopyErrorTextClick = () => {
    copyToClipboard(brokenStepError);
  };

  return (
    <div className={s.actionWizardBrokenStage__layout}>
      <div className={s.actionWizardBrokenStage__wrapper}>
        <div className={s.actionWizardBrokenStage__title}>
          <Icon size={28} name="triangle-alert" />
          <span>Something unexpected happened</span>
        </div>
        <div className={s.actionWizardBrokenStage__content}>
          <div>
            ADCM encountered{' '}
            <Button
              className={s.actionWizardBrokenStage__copyButton}
              variant="tertiary"
              onClick={handleCopyErrorTextClick}
            >
              <div>unknown error</div>
              <Icon name="g1-copy" />
            </Button>{' '}
            during this operation.
          </div>
          <div>
            If you wish to send us report, please use our{' '}
            <Link to={HelperLinkActions.Help} className="text-link">
              Community help
            </Link>{' '}
            or contact your designated Technical Support team so we can address your problem.
          </div>
        </div>
        <Button className={s.actionWizardBrokenStage__exitButton} variant="secondary" onClick={onClose}>
          Save & Exit
        </Button>
      </div>
    </div>
  );
};

export default ActionWizardBrokenStage;
