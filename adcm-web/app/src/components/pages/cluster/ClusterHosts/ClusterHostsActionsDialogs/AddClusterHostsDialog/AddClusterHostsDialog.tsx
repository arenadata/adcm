import { useDispatch, useStore } from '@hooks';
import { DialogV2 } from '@uikit';
import { closeCreateDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';
import ListTransfer from '@uikit/ListTransfer/ListTransfer';
import { useCreateClusterHostsForm } from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/AddClusterHostsDialog/useAddClusterHostsDialog';
import { useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import type { ListTransferItem } from '@uikit/ListTransfer/ListTransfer.types';
import s from './AddClusterHostsDialog.module.scss';

const availableHostsPanel = {
  title: 'Available hosts',
  searchPlaceholder: 'Search',
  actionButtonLabel: 'Select filtered',
};

const selectedHostsPanel = {
  title: 'Selected hosts',
  searchPlaceholder: 'Search',
  actionButtonLabel: 'Remove filtered',
};

const AddClusterHostsDialog = () => {
  const dispatch = useDispatch();

  const isOpenDialog = useStore(({ adcm }) => adcm.clusterHostsActions.createDialog.isOpen);

  const {
    formData,
    submit,
    resetForm,
    onChangeFormData,
    loadRelatedData,
    relatedData: { hostCandidatesOptions },
    isValid,
  } = useCreateClusterHostsForm();

  useEffect(() => {
    resetForm();
    if (isOpenDialog) {
      loadRelatedData();
    }
  }, [isOpenDialog, resetForm, loadRelatedData]);

  const srcList = useMemo<ListTransferItem[]>(() => {
    return hostCandidatesOptions.map(({ value, label }) => ({ key: value, label }));
  }, [hostCandidatesOptions]);

  const selectedHostIds = formData.selectedHostIds;
  const hasHostCandidates = hostCandidatesOptions.length > 0;

  const handleClusterHostsChange = (value: Set<number>) => {
    onChangeFormData({ selectedHostIds: value });
  };

  const handleCloseDialog = () => {
    dispatch(closeCreateDialog());
  };

  return (
    isOpenDialog && (
      <DialogV2
        title="Add hosts"
        onAction={submit}
        onCancel={handleCloseDialog}
        isActionDisabled={!isValid}
        actionButtonLabel="Add"
        width={hasHostCandidates ? '860px' : undefined}
        className={s.addClusterHostsDialog}
      >
        {hasHostCandidates && (
          <ListTransfer
            srcList={srcList}
            destKeys={selectedHostIds}
            onChangeDest={handleClusterHostsChange}
            srcOptions={availableHostsPanel}
            destOptions={selectedHostsPanel}
            className={s.addClusterHostsDialog__listTransfer}
          />
        )}
        {!hasHostCandidates && (
          <div>
            There are no available hosts. Create new hosts on the{' '}
            <Link className="text-link" to="/hosts" onClick={handleCloseDialog}>
              “Hosts”
            </Link>{' '}
            page.
          </div>
        )}
      </DialogV2>
    )
  );
};

export default AddClusterHostsDialog;
