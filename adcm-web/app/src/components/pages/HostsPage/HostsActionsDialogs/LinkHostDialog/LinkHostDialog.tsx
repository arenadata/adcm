import { DialogV2, FormField, FormFieldsContainer, Select } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { closeLinkDialog, linkHostsWithUpdate, loadClusters } from '@store/adcm/hosts/hostsActionsSlice';

const LinkHostDialog = () => {
  const dispatch = useDispatch();
  const hosts = useStore(({ adcm }) => adcm.hostsActions.linkDialog.hosts);
  const clusters = useStore(({ adcm }) => adcm.hostsActions.relatedData.clusters);

  const [clusterId, setClusterId] = useState<number | null>(null);

  const clustersOptions = useMemo(() => {
    return clusters.map(({ name, id }) => ({ value: id, label: name }));
  }, [clusters]);

  const reset = useCallback(() => {
    setClusterId(null);
  }, []);

  useEffect(() => {
    reset();

    if (hosts.length > 0) {
      dispatch(loadClusters());
    }
  }, [dispatch, hosts, reset]);

  const handleCloseDialog = useCallback(() => {
    dispatch(closeLinkDialog());
  }, [dispatch]);

  const handleConfirmDialog = useCallback(() => {
    if (!clusterId) {
      return;
    }

    dispatch(
      linkHostsWithUpdate({
        clusterId,
        hostIds: hosts.map(({ id }) => id),
      }),
    );
  }, [clusterId, dispatch, hosts]);

  if (hosts.length === 0) {
    return null;
  }

  return (
    <DialogV2
      title={hosts.length === 1 ? 'Link host' : 'Link hosts'}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      isActionDisabled={!clusterId}
      actionButtonLabel="Link"
    >
      <FormFieldsContainer>
        <FormField label="Cluster">
          <Select placeholder="Select cluster" value={clusterId} onChange={setClusterId} options={clustersOptions} />
        </FormField>
      </FormFieldsContainer>
    </DialogV2>
  );
};

export default LinkHostDialog;
