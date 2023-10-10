import { useEffect, useCallback } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { closeClusterRenameDialog, renameCluster } from '@store/adcm/clusters/clustersActionsSlice';
import { isClusterNameValid, required } from '@utils/validationsUtils';

interface RenameClusterFormData {
  name: string;
}

const initialFormData: RenameClusterFormData = {
  name: '',
};

export const useRenameClusterDialog = () => {
  const dispatch = useDispatch();

  const { isValid, formData, setFormData, handleChangeFormData, errors, setErrors } =
    useForm<RenameClusterFormData>(initialFormData);

  const { updateDialog } = useStore((s) => s.adcm.clustersActions);
  const clusters = useStore((s) => s.adcm.clusters.clusters);

  const isClusterNameUniq = useCallback(
    (name: string) => {
      return !clusters.find((cluster) => cluster.name === name);
    },
    [clusters],
  );

  useEffect(() => {
    if (updateDialog.cluster) {
      const { name } = updateDialog.cluster;
      setFormData({ name });
    }
  }, [updateDialog, setFormData]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Cluster name field is required') ||
        (isClusterNameValid(formData.name) ? undefined : 'Cluster name field is incorrect') ||
        (isClusterNameUniq(formData.name) ? undefined : 'Enter unique cluster name'),
    });
  }, [formData, setErrors, isClusterNameUniq]);

  const handleClose = () => {
    dispatch(closeClusterRenameDialog());
  };

  const handleRename = () => {
    if (updateDialog.cluster) {
      dispatch(
        renameCluster({
          id: updateDialog.cluster.id,
          name: formData.name,
        }),
      );
    }
  };

  return {
    isOpen: !!updateDialog.cluster,
    isValid,
    formData,
    errors,
    onClose: handleClose,
    onRename: handleRename,
    onChangeFormData: handleChangeFormData,
  };
};
