import React, { useMemo } from 'react';
import LicenseAcceptanceList from '@commonComponents/license/LicenseAcceptanceList/LicenseAcceptanceList';
import { useDispatch } from '@hooks';
import { AdcmComponentDependency, AdcmLicenseStatus } from '@models/adcm';
import { acceptServiceLicense } from '@store/adcm/cluster/services/servicesSlice';
import { RequiredServicesFormData } from '../RequiredServicesDialog.types';

interface ServicesLicensesStepProps {
  formData: RequiredServicesFormData;
  onChange: (changes: Partial<RequiredServicesFormData>) => void;
  unacceptedSelectedServices: AdcmComponentDependency[];
}

const ServicesLicensesStep: React.FC<ServicesLicensesStepProps> = ({
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
