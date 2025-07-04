import { Text, DialogV2 } from '@uikit';
import s from './AboutAdcmModal.module.scss';
import MainLogo from '@layouts/partials/MainLogo/MainLogo';
import { adcmVersion } from '@constants';

interface AboutAdcmProps {
  isOpen: boolean;
  onCancel: () => void;
}

const AboutAdcmModal = ({ isOpen, onCancel }: AboutAdcmProps) => {
  if (!isOpen) return null;

  return (
    <DialogV2 onCancel={onCancel} title="About ADCM" width="fit-content" dialogControls={<div />}>
      <div className={s.aboutAdcmModal}>
        <MainLogo className={s.aboutAdcmModal__logo} onClick={(e) => e.preventDefault()} />
        <div>
          <Text component="h3" variant="h2" className={s.aboutAdcmModal__subtitle}>
            Arenadata Cluster Manager
          </Text>
          version {adcmVersion}
        </div>
        <div className={s.aboutAdcmModal__rightsWrapper}>
          <p>© Arenadata Software LLC.</p>
          <p>All Rights Reserved.</p>
        </div>
      </div>
    </DialogV2>
  );
};

export default AboutAdcmModal;
