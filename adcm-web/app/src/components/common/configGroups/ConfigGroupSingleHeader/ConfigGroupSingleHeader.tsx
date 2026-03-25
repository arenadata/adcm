import type React from 'react';
import Panel from '@uikit/Panel/Panel';
import type { AdcmConfigGroup } from '@models/adcm';
import { Button, IconButton } from '@uikit';
import { Link } from 'react-router-dom';
import { useDispatch } from '@hooks';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import { openConfigGroupDescriptionDialog } from '@store/adcm/entityDescriptionDialog/entityDescriptionDialogSlice';
import type {
  ConfigGroupOwner,
  ConfigGroupEntityArgs,
} from '@store/adcm/entityDescriptionDialog/entityDescriptionDialog.types';
import s from './ConfigGroupSingleHeader.module.scss';

const NO_DESCRIPTION_PLACEHOLDER = 'No description yet. Add one to provide more context.';

interface ConfigGroupSingleHeaderProps {
  configGroup: AdcmConfigGroup | null;
  returnUrl: string;
  entityType: ConfigGroupOwner;
  entityArgs: ConfigGroupEntityArgs;
}

const ConfigGroupSingleHeader: React.FC<ConfigGroupSingleHeaderProps> = ({
  configGroup,
  returnUrl,
  entityType,
  entityArgs,
}) => {
  const dispatch = useDispatch();

  const handleEditDescription = () => {
    if (configGroup) {
      dispatch(openConfigGroupDescriptionDialog({ configGroup, entityType, entityArgs }));
    }
  };

  const descriptionText = configGroup?.description || NO_DESCRIPTION_PLACEHOLDER;

  return (
    <div className={s.configGroupSingleHeader}>
      <Panel className={s.configGroupSingleHeader__top}>
        <strong>{configGroup?.name}</strong>
        <Link to={returnUrl} className="flex-inline">
          <Button variant="secondary">Return back</Button>
        </Link>
      </Panel>
      <FlexGroup gap="8px" justifyContent="space-between">
        <span className={s.configGroupSingleHeader__descriptionText}>{descriptionText}</span>
        <IconButton icon="g1-edit" size={28} onClick={handleEditDescription} />
      </FlexGroup>
    </div>
  );
};

export default ConfigGroupSingleHeader;
