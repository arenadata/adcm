import { Dialog, FormField, FormFieldsContainer, Select } from '@uikit';
import { useLinkHostForm } from './useLinkHostForm';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { closeLinkDialog } from '@store/adcm/hosts/hostsActionsSlice';

const LinkHostDialog = () => {
  const dispatch = useDispatch();

  const linkableHost = useStore(
    ({
      adcm: {
        hosts: { hosts },
        hostsActions: {
          linkDialog: { id: linkableId },
        },
      },
    }) => {
      if (!linkableId) return null;
      return hosts.find(({ id }) => id === linkableId) ?? null;
    },
  );

  const {
    formData,
    submit,
    reset,
    onChangeFormData,
    loadRelatedData,
    relatedData: { clustersOptions },
    isValid,
  } = useLinkHostForm();

  useEffect(() => {
    reset();
    if (linkableHost) {
      loadRelatedData();
      onChangeFormData({ hostId: linkableHost.id });
    }
  }, [linkableHost, reset, loadRelatedData, onChangeFormData]);

  const isOpenLink = !!linkableHost;

  const handleCloseDialog = () => {
    dispatch(closeLinkDialog());
  };

  const handleClusterChange = (value: number | null) => {
    onChangeFormData({ clusterId: value });
  };

  return (
    <Dialog
      title="Link host"
      isOpen={isOpenLink}
      onOpenChange={handleCloseDialog}
      onAction={submit}
      isActionDisabled={!isValid}
      actionButtonLabel="Link"
    >
      <FormFieldsContainer>
        <FormField label="Cluster">
          <Select
            placeholder="Select cluster"
            value={formData.clusterId}
            onChange={handleClusterChange}
            options={clustersOptions}
          />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default LinkHostDialog;
