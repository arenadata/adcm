import type React from 'react';
import { useMemo, useState } from 'react';
import { Dialog, TabsBlock } from '@uikit';
import cn from 'classnames';
import s from './LicenseAcceptanceDialog.module.scss';
import TabButton from '@uikit/Tabs/TabButton';
import { AdcmLicenseStatus } from '@models/adcm';
import type { LicenseAcceptanceDialogProps } from '@commonComponents/Dialog/LicenseAcceptanceDialog/LicenseAcceptanceDialog.types';
import LicenseAcceptPanel from '@commonComponents/Dialog/LicenseAcceptanceDialog/LicenseAcceptPanel/LicenseAcceptPanel';

const LicenseAcceptanceDialog: React.FC<LicenseAcceptanceDialogProps> = ({
  dialogTitle,
  licensesRequiringAcceptanceList,
  isOpen,
  onCloseClick,
  onAcceptLicense,
  customControls,
}) => {
  const steps = useMemo(() => {
    return licensesRequiringAcceptanceList?.map((license) => ({
      key: license.name,
      id: license.id,
      title: license.displayName,
      licenseStatus: license.license.status,
      licenseText: license.license.text,
    }));
  }, [licensesRequiringAcceptanceList]);
  const [currentStep, setCurrentStep] = useState(steps[0].key);
  const currentLicense = useMemo(() => steps.find((license) => license.key === currentStep), [steps, currentStep]);

  const handleCloseDialog = () => {
    onCloseClick();
  };

  const handleChangeStep = (event: React.MouseEvent<HTMLButtonElement>) => {
    const stepKey = event.currentTarget.dataset.stepKey ?? '';
    setCurrentStep(stepKey);
  };

  return (
    <Dialog
      title={dialogTitle}
      isOpen={isOpen}
      onOpenChange={handleCloseDialog}
      width="65%"
      dialogControls={customControls}
    >
      {steps?.length > 0 && (
        <TabsBlock variant="secondary">
          {steps.map((step) => (
            <TabButton
              isActive={currentStep === step.key}
              data-step-key={step.key}
              onClick={handleChangeStep}
              key={step.key}
              className={cn({
                [s.licenseTab__button_licenseAccepted]: step.licenseStatus === AdcmLicenseStatus.Accepted,
              })}
            >
              {step.title}
            </TabButton>
          ))}
        </TabsBlock>
      )}
      {currentLicense && (
        <LicenseAcceptPanel key={currentLicense.key} license={currentLicense} onAcceptLicense={onAcceptLicense} />
      )}
    </Dialog>
  );
};
export default LicenseAcceptanceDialog;
