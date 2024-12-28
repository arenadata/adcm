import { Dialog, FormField, FormFieldsContainer, Select } from '@uikit';
import { useLinkHostForm } from './useLinkHostForm';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { closeLinkDialog } from '@store/adcm/hosts/hostsActionsSlice';

const LinkHostDialog = () => {
  const dispatch = useDispatch();

  const host = useStore(({ adcm }) => adcm.hostsActions.linkDialog.host);

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
    if (host) {
      loadRelatedData();
      onChangeFormData({ hostId: host.id });
    }
  }, [host, reset, loadRelatedData, onChangeFormData]);

  const isOpenLink = !!host;

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
