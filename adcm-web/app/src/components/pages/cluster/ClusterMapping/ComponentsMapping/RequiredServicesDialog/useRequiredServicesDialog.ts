import { useMemo, useState } from 'react';
import {
  closeRequiredServicesDialog,
  getMappings,
  getNotAddedServices,
} from '@store/adcm/cluster/mapping/mappingSlice';
import { useDispatch, useForm, useStore } from '@hooks';
import { AdcmLicenseStatus } from '@models/adcm';
import { RequiredServicesFormData, RequiredServicesStepKey } from './RequiredServicesDialog.types';
import { addServices } from '@store/adcm/cluster/services/servicesActionsSlice';

const getInitRequiredServicesFormData = () => ({
  serviceCandidatesAcceptedLicense: new Set<number>(),
});

export const useRequiredServicesDialog = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const srcComponent = useStore(({ adcm }) => adcm.clusterMapping.requiredServicesDialog.component);
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);

  const { formData, setFormData, handleChangeFormData } = useForm<RequiredServicesFormData>(
    getInitRequiredServicesFormData(),
  );

  const dependsServices = useMemo(() => {
    if (!srcComponent?.dependOn?.length) return [];

    return srcComponent.dependOn
      .filter(({ servicePrototype }) => !!notAddedServicesDictionary[servicePrototype.id])
      .map((s) => s.servicePrototype);
  }, [notAddedServicesDictionary, srcComponent]);

  const unacceptedDependsServices = useMemo(() => {
    return dependsServices.filter(({ license }) => license.status === AdcmLicenseStatus.Unaccepted);
  }, [dependsServices]);

  const [currentStep, setCurrentStep] = useState(RequiredServicesStepKey.ShowServices);

  const switchToLicenseStep = () => {
    setCurrentStep(RequiredServicesStepKey.ServicesLicenses);
  };

  const isValid = useMemo(() => {
    if (currentStep === RequiredServicesStepKey.ShowServices) return true;

    if (currentStep === RequiredServicesStepKey.ServicesLicenses) {
      // all unacceptedServices already accepted
      return unacceptedDependsServices.every(({ id }) => formData.serviceCandidatesAcceptedLicense.has(id));
    }

    return true;
  }, [formData.serviceCandidatesAcceptedLicense, currentStep, unacceptedDependsServices]);

  const onClose = () => {
    setFormData(getInitRequiredServicesFormData());
    dispatch(closeRequiredServicesDialog());
  };

  const onSubmit = () => {
    if (cluster) {
      const clusterId = cluster.id;
      dispatch(
        addServices({
          clusterId: clusterId,
          servicesIds: dependsServices.map((s) => s.id),
        }),
      )
        .unwrap()
        .then(() => {
          dispatch(getMappings({ clusterId }));
          dispatch(getNotAddedServices({ clusterId }));
        });
    }
    onClose();
  };

  return {
    isOpen: srcComponent !== null,
    onClose,
    onSubmit,
    currentStep,
    formData,
    handleChangeFormData,
    switchToLicenseStep,
    dependsServices,
    unacceptedDependsServices,
    isValid,
  };
};
