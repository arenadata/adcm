import React, { useMemo } from 'react';
import { useStore } from '@hooks';
import { FormFieldsContainer, MultiSelectPanel, Spinner } from '@uikit';
import type { AddClusterServicesStepProps } from '../AddClusterServiceDialog.types';
import ServicesDependenciesWarning from '../ServicesDependenciesWarning/ServicesDependenciesWarning';
import WarningMessage from '@uikit/WarningMessage/WarningMessage';
import s from './SelectServicesStep.module.scss';
import type { AdcmServicePrototype } from '@models/adcm';

const SelectServicesStep: React.FC<AddClusterServicesStepProps> = ({
  formData,
  onChange,
  unacceptedSelectedServices,
}) => {
  const serviceCandidates = useStore(({ adcm }) => adcm.servicesActions.relatedData.serviceCandidates);
  const isLoading = useStore(({ adcm }) => adcm.servicesActions.relatedData.isServiceCandidatesLoading);

  const servicesDependencies = useMemo<AdcmServicePrototype[]>(() => {
    return serviceCandidates.filter(
      ({ id, dependOn }) => formData.selectedServicesIds.includes(id) && dependOn && dependOn.length > 0,
    );
  }, [formData, serviceCandidates]);

  const hasUnacceptedSelectedServices = unacceptedSelectedServices.length > 0;

  const serviceCandidatesOptions = useMemo(() => {
    return serviceCandidates.map((serviceCandidate) => ({
      label: serviceCandidate.displayName,
      value: serviceCandidate.id,
    }));
  }, [serviceCandidates]);

  const handleClusterServicesChange = (selectedServicesIds: number[]) => {
    onChange({ selectedServicesIds });
  };

  const isEmptyList = serviceCandidatesOptions.length === 0;

  return (
    <FormFieldsContainer>
      {isLoading ? (
        <Spinner />
      ) : (
        <>
          {isEmptyList && <div>There are no new services. Your cluster already has all of them.</div>}
          {!isEmptyList && (
            <MultiSelectPanel
              options={serviceCandidatesOptions}
              value={formData.selectedServicesIds}
              onChange={handleClusterServicesChange}
              checkAllLabel="All services"
              searchPlaceholder="Search services"
              isSearchable={true}
              compactMode={true}
            />
          )}
          {servicesDependencies.length > 0 && (
            <ServicesDependenciesWarning
              className={s.selectServicesStep__warning}
              dependenciesList={servicesDependencies}
            />
          )}
          {hasUnacceptedSelectedServices && (
            <WarningMessage
              className={s.selectServicesStep__warning}
              children="Services you selected require you to accept Terms of Agreement"
            />
          )}
        </>
      )}
    </FormFieldsContainer>
  );
};
export default SelectServicesStep;
