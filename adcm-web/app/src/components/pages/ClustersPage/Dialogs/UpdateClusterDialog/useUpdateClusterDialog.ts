import { useEffect, useCallback, useMemo } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { closeClusterRenameDialog, renameCluster } from '@store/adcm/clusters/clustersActionsSlice';
import { isClusterNameValid, required } from '@utils/validationsUtils';

interface RenameClusterFormData {
  name: string;
}

const initialFormData: RenameClusterFormData = {
  name: '',
};

export const useUpdateClusterDialog = () => {
  const dispatch = useDispatch();

  const { isValid, formData, setFormData, handleChangeFormData, errors, setErrors } =
    useForm<RenameClusterFormData>(initialFormData);

  const updatedCluster = useStore((s) => s.adcm.clustersActions.updateDialog.cluster);
  const clusters = useStore((s) => s.adcm.clusters.clusters);

  const isNameChanged = useMemo(() => {
    return formData.name !== updatedCluster?.name;
  }, [formData, updatedCluster]);

  const isClusterNameUniq = useCallback(
    (name: string) => {
      return !clusters.find((cluster) => cluster.name === name && cluster.id !== updatedCluster?.id);
    },
    [clusters, updatedCluster],
  );

  useEffect(() => {
    if (updatedCluster) {
      const { name } = updatedCluster;
      setFormData({ name });
    }
  }, [updatedCluster, setFormData]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Cluster name field is required') ||
        (isClusterNameValid(formData.name) ? undefined : 'Cluster name field is incorrect') ||
        (isClusterNameUniq(formData.name) ? undefined : 'Cluster with the same name already exists'),
    });
  }, [formData, setErrors, isClusterNameUniq]);

  const handleClose = () => {
    dispatch(closeClusterRenameDialog());
  };

  const handleRename = () => {
    if (updatedCluster) {
      dispatch(
        renameCluster({
          id: updatedCluster.id,
          name: formData.name,
        }),
      );
    }
  };

  return {
    isOpen: !!updatedCluster,
    isValid: isValid && isNameChanged,
    formData,
    errors,
    onClose: handleClose,
    onRename: handleRename,
    onChangeFormData: handleChangeFormData,
  };
};
