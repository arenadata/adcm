import { DialogV2, FormField, FormFieldsContainer, Select } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { closeShareDialog, createHostDuplicates, loadClusters } from '@store/adcm/hosts/hostsActionsSlice';

const ShareHostDialog = () => {
  const dispatch = useDispatch();
  const hosts = useStore(({ adcm }) => adcm.hostsActions.shareDialog.hosts);
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
    dispatch(closeShareDialog());
  }, [dispatch]);

  const handleConfirmDialog = useCallback(() => {
    dispatch(
      createHostDuplicates(
        hosts.map((host) => ({
          hostId: host.id,
          name: host.name,
          clusterId,
        })),
      ),
    );
  }, [clusterId, dispatch, hosts]);

  if (hosts.length === 0) {
    return null;
  }

  return (
    <DialogV2
      title={hosts.length === 1 ? 'Create subhost' : 'Create subhosts'}
      onAction={handleConfirmDialog}
      onCancel={handleCloseDialog}
      actionButtonLabel="Create"
    >
      <FormFieldsContainer>
        <FormField label="Add new subhosts to the cluster:">
          <Select placeholder="Select cluster" value={clusterId} onChange={setClusterId} options={clustersOptions} />
        </FormField>
      </FormFieldsContainer>
    </DialogV2>
  );
};

export default ShareHostDialog;
