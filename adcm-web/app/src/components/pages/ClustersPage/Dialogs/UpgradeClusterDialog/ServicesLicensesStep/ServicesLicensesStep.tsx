import React, { useMemo } from 'react';
import LicenseAcceptanceList from '@commonComponents/license/LicenseAcceptanceList/LicenseAcceptanceList';
import { useDispatch, useStore } from '@hooks';
import { UpgradeStepFormProps } from '@pages/ClustersPage/Dialogs/UpgradeClusterDialog/UpgradeClusterDialog.types';
import { AdcmLicenseStatus } from '@models/adcm';
import { acceptPrototypeLicense } from '@store/adcm/clusters/clusterUpgradesSlice';

const ServicesLicensesStep: React.FC<UpgradeStepFormProps> = ({ formData, onChange }) => {
  const dispatch = useDispatch();

  const upgradesDetails = useStore(({ adcm }) => adcm.clusterUpgrades.relatedData.upgradesDetails);
  const upgradeDetails = (formData.upgradeId && upgradesDetails[formData.upgradeId]) || null;

  const unacceptedServicesPrototypes = useMemo(() => {
    return (
      upgradeDetails?.bundle.unacceptedServicesPrototypes.map(({ id, license, ...servicePrototype }) => ({
        id,
        ...servicePrototype,
        license: {
          ...license,
          status: formData.servicesPrototypesAcceptedLicense.has(id)
            ? AdcmLicenseStatus.Accepted
            : AdcmLicenseStatus.Unaccepted,
        },
      })) ?? []
    );
  }, [upgradeDetails, formData]);

  const handleAccept = (servicePrototypeId: number) => {
    dispatch(acceptPrototypeLicense(servicePrototypeId))
      .unwrap()
      .then(() => {
        formData.servicesPrototypesAcceptedLicense.add(servicePrototypeId);
        onChange({ servicesPrototypesAcceptedLicense: new Set(formData.servicesPrototypesAcceptedLicense) });
      });
  };

  return (
    <div>
      <LicenseAcceptanceList items={unacceptedServicesPrototypes} onAccept={handleAccept} />
    </div>
  );
};

export default ServicesLicensesStep;
