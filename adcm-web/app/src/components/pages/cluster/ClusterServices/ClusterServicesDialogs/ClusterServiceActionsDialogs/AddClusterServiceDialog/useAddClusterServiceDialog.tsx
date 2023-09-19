import { useDispatch, useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  addService,
  cleanupServicesActions,
  closeAddDialog,
  openServiceAddDialog,
} from '@store/adcm/cluster/services/servicesActionsSlice';
import { AdcmLicenseStatus, AdcmPrototype, AdcmServiceDependOnService } from '@models/adcm';
import { acceptServiceLicense as acceptLicense, getServicesLicenses } from '@store/adcm/cluster/services/servicesSlice';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';

export interface AddClusterServicesFormData {
  clusterId: number | null;
  serviceIds: number[];
}

const initialFormData: AddClusterServicesFormData = {
  clusterId: null,
  serviceIds: [],
};

export const useAddClusterServiceForm = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const isOpen = useStore(({ adcm }) => adcm.servicesActions.isAddServiceDialogOpen);
  const servicesInTable = useStore(({ adcm }) => adcm.services.services);
  const servicePrototypes = useStore(({ adcm }) => adcm.servicesActions.relatedData.servicePrototypes);
  const serviceLicenses = useStore(({ adcm }) => adcm.services.serviceLicense);
  const servicesInTableIds = useMemo(() => servicesInTable.map((service) => service.prototype.id), [servicesInTable]);
  const nonAppendedServices = useMemo(
    () => servicePrototypes.filter(({ id }) => !servicesInTableIds.includes(id)),
    [servicePrototypes, servicesInTableIds],
  );

  const [formData, setFormData] = useState<AddClusterServicesFormData>(initialFormData);
  const [processedServiceData, setProcessedServiceData] = useState<AddClusterServicesFormData>(initialFormData);
  const [isLicenseAcceptanceDialogOpen, setLicenseAcceptanceDialogOpen] = useState(false);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen]);

  const nonAppendedServicesWithDeps = useMemo(() => {
    const { serviceIds } = formData;

    return nonAppendedServices.filter(
      (service) => serviceIds.includes(service.id) && service.dependOn && service.dependOn.length > 0,
    );
  }, [formData, nonAppendedServices]);

  const servicePrototypesOptions = useMemo(() => {
    return nonAppendedServices.map(({ name, id }) => ({ value: id, label: name }));
  }, [nonAppendedServices]);

  const isServicesWithLicenseSelected = useMemo(() => {
    const { serviceIds } = formData;

    return !!nonAppendedServices.find(
      (service) => serviceIds.includes(service.id) && service.licenseStatus === AdcmLicenseStatus.Unaccepted,
    );
  }, [formData, nonAppendedServices]);

  const servicesWithDependencies = useMemo(() => {
    const { serviceIds } = formData;

    return nonAppendedServicesWithDeps
      .flatMap((service) =>
        (service.dependOn as AdcmServiceDependOnService[]).map((dependOnService) => ({
          ...dependOnService,
          dependableService: service.name,
        })),
      )
      .filter(
        (service) => !servicesInTableIds.includes(service.prototypeId) && !serviceIds.includes(service.prototypeId),
      );
  }, [formData, nonAppendedServicesWithDeps, servicesInTableIds]);

  const servicesWithDependenciesList = useMemo(() => {
    return nonAppendedServicesWithDeps.map((service) => ({
      id: service.id,
      displayName: service.displayName,
      dependencies: servicesWithDependencies.filter(({ dependableService }) => service.name === dependableService),
    }));
  }, [servicesWithDependencies, nonAppendedServicesWithDeps]);

  const isServicesAndDependenciesChecked = useMemo(() => {
    const { serviceIds } = formData;

    if (servicesWithDependencies.length > 0 && serviceIds.length > 0) {
      return (
        [...new Set([...servicesWithDependencies.map((service) => service?.prototypeId), ...serviceIds])]
          .sort()
          .join() === serviceIds.join()
      );
    }

    return serviceIds.length > 0;
  }, [formData, servicesWithDependencies]);

  const isValid = useMemo(() => {
    const { serviceIds } = formData;
    return serviceIds.length > 0 && isServicesAndDependenciesChecked;
  }, [formData, isServicesAndDependenciesChecked]);

  const resetForm = useCallback(() => {
    setFormData(initialFormData);
  }, []);

  const openLicenseAcceptanceDialog = useCallback(() => {
    setLicenseAcceptanceDialogOpen(true);
    setProcessedServiceData(formData);
    dispatch(cleanupServicesActions());
  }, [dispatch, formData]);

  const submit = useCallback(() => {
    const { serviceIds } = isLicenseAcceptanceDialogOpen ? processedServiceData : formData;

    if (serviceIds.length > 0) {
      dispatch(
        addService({
          clusterId: clusterId ?? undefined,
          serviceIds,
        }),
      );
    }

    dispatch(cleanupServicesActions);

    if (isLicenseAcceptanceDialogOpen) {
      setLicenseAcceptanceDialogOpen(false);
    } else {
      dispatch(closeAddDialog());
    }
  }, [isLicenseAcceptanceDialogOpen, processedServiceData, formData, dispatch, clusterId]);

  const getLicenses = (serviceIds: number[]) => {
    if (serviceIds.length > 0) {
      dispatch(getServicesLicenses(serviceIds));
    }
  };

  const acceptServiceLicense = (serviceId: number) => {
    dispatch(acceptLicense(serviceId));
  };

  const handleClose = () => {
    dispatch(cleanupServicesActions());
  };

  const handleLicenseAcceptanceDialogClose = () => {
    setLicenseAcceptanceDialogOpen(false);
    dispatch(cleanupServicesActions());
    dispatch(closeAddDialog());
  };

  const handleLicenseAcceptanceDialogBack = () => {
    setLicenseAcceptanceDialogOpen(false);
    dispatch(openServiceAddDialog(clusterId));
  };

  const handleChangeFormData = (changes: Partial<AddClusterServicesFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  const isAllLicensesAccepted = (licenses: Omit<AdcmPrototype, 'type' | 'description' | 'bundleId'>[] | []) => {
    return licenses?.every((step) => step.license.status === AdcmLicenseStatus.Accepted);
  };

  const dialogControls = (
    <CustomDialogControls
      actionButtonLabel="Add"
      cancelButtonLabel={'Back'}
      isActionDisabled={!isAllLicensesAccepted(serviceLicenses)}
      onCancel={handleLicenseAcceptanceDialogBack}
      onAction={submit}
    />
  );

  return {
    isOpen,
    isLicenseAcceptanceDialogOpen,
    isValid,
    formData,
    resetForm,
    submit,
    getLicenses,
    dialogControls,
    onClose: handleClose,
    onCloseLicenseAcceptanceDialog: handleLicenseAcceptanceDialogClose,
    onOpenLicenseAcceptanceDialog: openLicenseAcceptanceDialog,
    onChangeFormData: handleChangeFormData,
    onAcceptServiceLicense: acceptServiceLicense,
    relatedData: {
      servicesWithDependenciesList,
      isServicesWithLicenseSelected,
      servicePrototypesOptions,
      serviceLicenses,
    },
  };
};
