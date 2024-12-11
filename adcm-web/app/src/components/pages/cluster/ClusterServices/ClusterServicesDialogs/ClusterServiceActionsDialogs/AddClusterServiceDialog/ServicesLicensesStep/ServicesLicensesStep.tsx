import type React from 'react';
import { useMemo } from 'react';
import LicenseAcceptanceList from '@commonComponents/license/LicenseAcceptanceList/LicenseAcceptanceList';
import { useDispatch } from '@hooks';
import { AdcmLicenseStatus } from '@models/adcm';
import type { AddClusterServicesStepProps } from '../AddClusterServiceDialog.types';
import { acceptServiceLicense } from '@store/adcm/cluster/services/servicesSlice';

const ServicesLicensesStep: React.FC<AddClusterServicesStepProps> = ({
  formData,
  onChange,
  unacceptedSelectedServices,
}) => {
  const dispatch = useDispatch();

  const unacceptedServicesPrototypes = useMemo(() => {
    return (
      unacceptedSelectedServices.map(({ id, license, ...servicePrototype }) => ({
        id,
        ...servicePrototype,
        license: {
          ...license,
          status: formData.serviceCandidatesAcceptedLicense.has(id)
            ? AdcmLicenseStatus.Accepted
            : AdcmLicenseStatus.Unaccepted,
        },
      })) ?? []
    );
  }, [unacceptedSelectedServices, formData]);

  const handleAccept = (servicePrototypeId: number) => {
    dispatch(acceptServiceLicense(servicePrototypeId))
      .unwrap()
      .then(() => {
        formData.serviceCandidatesAcceptedLicense.add(servicePrototypeId);
        onChange({ serviceCandidatesAcceptedLicense: new Set(formData.serviceCandidatesAcceptedLicense) });
      });
  };

  return (
    <div>
      <LicenseAcceptanceList items={unacceptedServicesPrototypes} onAccept={handleAccept} />
    </div>
  );
};

export default ServicesLicensesStep;
