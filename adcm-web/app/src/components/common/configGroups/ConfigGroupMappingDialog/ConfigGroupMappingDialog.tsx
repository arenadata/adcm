import React, { useEffect, useMemo } from 'react';
import { AdcmConfigGroup, AdcmHost, AdcmHostCandidate } from '@models/adcm';
import { Dialog } from '@uikit';
import ListTransfer from '@uikit/ListTransfer/ListTransfer';
import { useForm } from '@hooks';

interface ConfigGroupMappingDialogProps {
  configGroup: AdcmConfigGroup | null;
  onSubmit: (configGroupId: number, mappedHostsIds: number[]) => void;
  onClose: () => void;
  isSaveMapping: boolean;

  candidatesHosts: AdcmHostCandidate[];
}

type MappedHostsKeys = Set<AdcmHost['id']>;

type FormData = {
  mappedHostsKeys: MappedHostsKeys;
};

type FormErrors = {
  srcErrorMessage?: string;
  destErrorMessage?: string;
};

const initFormData: FormData = {
  mappedHostsKeys: new Set(),
};

const transferOptions = {
  searchPlaceholder: 'Search hosts',
};

const ConfigGroupMappingDialog: React.FC<ConfigGroupMappingDialogProps> = ({
  configGroup,
  onSubmit,
  onClose,
  candidatesHosts,
  isSaveMapping,
}) => {
  const isOpen = configGroup !== null;
  const { isValid, setErrors, errors, formData, setFormData } = useForm<FormData, FormErrors>(initFormData);

  const srcOptions = useMemo(() => {
    // we should concat both hosts lists. We should show mapped hosts in SRC side as selected items
    // if user deselected host in DEST side, then he should be able to select this host in SRC once more
    return candidatesHosts.concat(configGroup?.hosts ?? []).map(({ id, name }) => ({ key: id, label: name }));
  }, [candidatesHosts, configGroup]);

  useEffect(() => {
    !isOpen && setFormData(initFormData);
  }, [isOpen, setFormData]);

  useEffect(() => {
    setFormData({
      mappedHostsKeys: new Set(configGroup?.hosts.map(({ id }) => id)),
    });
  }, [configGroup, setFormData]);

  useEffect(() => {
    setErrors({
      srcErrorMessage: srcOptions.length > 0 ? undefined : 'The cluster should have some hosts linked',
      destErrorMessage: formData.mappedHostsKeys.size > 0 ? undefined : 'Can not set mapping without selected hosts',
    });
  }, [formData.mappedHostsKeys, srcOptions, setErrors]);

  const handleChangeMapping = (hostKeys: MappedHostsKeys) => {
    setFormData({
      mappedHostsKeys: hostKeys,
    });
  };

  const handleSubmit = () => {
    configGroup && onSubmit(configGroup.id, [...formData.mappedHostsKeys]);
  };

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={onClose}
      title={`Mapping config group "${configGroup?.name}" to hosts`}
      onAction={handleSubmit}
      actionButtonLabel="Save"
      isActionDisabled={!isValid || isSaveMapping}
      width="860px"
    >
      <ListTransfer
        srcList={srcOptions}
        destKeys={formData.mappedHostsKeys}
        onChangeDest={handleChangeMapping}
        srcOptions={transferOptions}
        destOptions={transferOptions}
        srcError={errors.srcErrorMessage}
        destError={errors.destErrorMessage}
      />
    </Dialog>
  );
};
export default ConfigGroupMappingDialog;
