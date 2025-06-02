import { DialogV2, FormField, FormFieldsContainer, Select } from '@uikit';
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

  if (!host) return null;

  const handleCloseDialog = () => {
    dispatch(closeLinkDialog());
  };

  const handleClusterChange = (value: number | null) => {
    onChangeFormData({ clusterId: value });
  };

  return (
    <DialogV2
      title="Link host"
      onAction={submit}
      onCancel={handleCloseDialog}
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
    </DialogV2>
  );
};

export default LinkHostDialog;
