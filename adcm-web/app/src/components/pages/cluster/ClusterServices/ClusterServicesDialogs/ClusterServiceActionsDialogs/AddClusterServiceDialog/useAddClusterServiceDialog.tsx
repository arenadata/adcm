import { useDispatch, useForm, useStore } from '@hooks';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  addServicesWithUpdate,
  closeCreateDialog,
  getServiceCandidates,
} from '@store/adcm/cluster/services/servicesActionsSlice';
import type { AddClusterServicesFormData } from './AddClusterServiceDialog.types';
import { AddServiceStepKey } from './AddClusterServiceDialog.types';
import { AdcmLicenseStatus } from '@models/adcm';

const getInitialFormData = (): AddClusterServicesFormData => ({
  clusterId: null,
  selectedServicesIds: [],
  serviceCandidatesAcceptedLicense: new Set(),
});

export const useAddClusterServiceDialog = () => {
  const dispatch = useDispatch();

  const { formData, handleChangeFormData, setFormData } = useForm<AddClusterServicesFormData>(getInitialFormData());
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const isOpen = useStore(({ adcm }) => adcm.servicesActions.createDialog.isOpen);
  const serviceCandidates = useStore(({ adcm }) => adcm.servicesActions.relatedData.serviceCandidates);

  const [currentStep, setCurrentStep] = useState(AddServiceStepKey.SelectServices);

  useEffect(() => {
    if (isOpen && cluster) {
      dispatch(getServiceCandidates(cluster.id));
    }
  }, [isOpen, cluster, dispatch]);

  const unacceptedSelectedServices = useMemo(() => {
    return serviceCandidates.filter(
      ({ id, license }) => license.status === AdcmLicenseStatus.Unaccepted && formData.selectedServicesIds.includes(id),
    );
  }, [formData.selectedServicesIds, serviceCandidates]);

  const handleClose = useCallback(() => {
    setCurrentStep(AddServiceStepKey.SelectServices);
    setFormData(getInitialFormData());
    dispatch(closeCreateDialog());
  }, [setFormData, setCurrentStep, dispatch]);

  const switchToLicenseStep = () => {
    setCurrentStep(AddServiceStepKey.ServicesLicenses);
  };

  const handleSubmit = () => {
    if (cluster) {
      dispatch(
        addServicesWithUpdate({
          clusterId: cluster.id,
          servicesIds: formData.selectedServicesIds,
        }),
      );
      handleClose();
    }
  };

  const isValid = useMemo(() => {
    // when user not select services disabled submit
    if (formData.selectedServicesIds.length === 0) return false;

    if (currentStep === AddServiceStepKey.SelectServices) {
      return (
        serviceCandidates
          // search only selected services
          .filter(({ id }) => formData.selectedServicesIds.includes(id))
          // check that for every selected services all their dependencies services selected too
          .every(({ dependOn }) => {
            return (
              dependOn?.every(({ servicePrototype }) => formData.selectedServicesIds.includes(servicePrototype.id)) ??
              true
            );
          })
      );
    }

    if (currentStep === AddServiceStepKey.ServicesLicenses) {
      // all unacceptedServices already accepted
      return unacceptedSelectedServices.every(({ id }) => formData.serviceCandidatesAcceptedLicense.has(id));
    }

    return true;
  }, [currentStep, formData, serviceCandidates, unacceptedSelectedServices]);

  return {
    isOpen,
    currentStep,
    onSubmit: handleSubmit,
    onClose: handleClose,
    formData,
    handleChangeFormData,
    isValid,
    switchToLicenseStep,
    unacceptedSelectedServices,
  };
};
