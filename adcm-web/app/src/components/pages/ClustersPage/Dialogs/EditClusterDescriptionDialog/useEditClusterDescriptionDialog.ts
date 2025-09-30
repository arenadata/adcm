import { useEffect, useMemo } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { closeClusterDescriptionChangeDialog, editDescription } from '@store/adcm/clusters/clustersActionsSlice';

interface EditDescriptionClusterFormData {
  description: string;
}

const initialFormData: EditDescriptionClusterFormData = {
  description: '',
};

export const useEditClusterDescriptionDialog = () => {
  const dispatch = useDispatch();

  const { isValid, formData, setFormData, handleChangeFormData, setErrors, errors } =
    useForm<EditDescriptionClusterFormData>(initialFormData);

  const cluster = useStore((s) => s.adcm.clustersActions.descriptionDialog.cluster);

  const isDescriptionChanged = useMemo(() => {
    return formData.description !== cluster?.description;
  }, [formData, cluster]);

  useEffect(() => {
    if (cluster?.id) {
      const { description } = cluster;
      setFormData({ description });
    }
  }, [cluster?.id, setFormData]);

  useEffect(() => {
    setErrors({
      description: formData.description.length <= 256 ? undefined : 'Description should be shorter or equal to 256',
    });
  }, [formData, setErrors]);

  const handleClose = () => {
    dispatch(closeClusterDescriptionChangeDialog());
  };

  const handleEditDescription = () => {
    if (cluster) {
      dispatch(
        editDescription({
          id: cluster.id,
          description: formData.description,
        }),
      );
    }
  };

  return {
    hasClusterForUpdate: !!cluster,
    isValid: isValid && isDescriptionChanged,
    formData,
    errors,
    onClose: handleClose,
    onEditDescription: handleEditDescription,
    onChangeFormData: handleChangeFormData,
  };
};
