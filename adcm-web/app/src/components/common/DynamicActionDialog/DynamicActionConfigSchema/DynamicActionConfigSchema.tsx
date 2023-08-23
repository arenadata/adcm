import React, { useState } from 'react';
import ToolbarPanel from '@uikit/ToolbarPanel/ToolbarPanel';
import { Button, ButtonGroup, SearchInput } from '@uikit';
import { DynamicActionCommonOptions } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import s from '../DynamicActionDialog.module.scss';
import { getDefaultConfigSchemaRunConfig } from '@commonComponents/DynamicActionDialog/DynamicActionDialog.utils';

interface DynamicActionConfigSchemaProps extends DynamicActionCommonOptions {
  submitLabel?: string;
}

const DynamicActionConfigSchema: React.FC<DynamicActionConfigSchemaProps> = ({
  actionDetails,
  onSubmit,
  onCancel,
  submitLabel = 'Run',
}) => {
  const [localConfigSchema, setLocalConfigSchema] = useState(() => {
    return getDefaultConfigSchemaRunConfig().config;
  });

  const handleResetClick = () => {
    setLocalConfigSchema({});
  };

  const handleSubmit = () => {
    onSubmit({ config: localConfigSchema });
  };

  return (
    <div>
      <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
        <SearchInput placeholder="Search input" />
        <ButtonGroup>
          <Button variant="secondary" iconLeft="g1-return" onClick={handleResetClick} />
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>{submitLabel}</Button>
        </ButtonGroup>
      </ToolbarPanel>

      <div>{JSON.stringify(actionDetails.configSchema, null, '\n')}</div>
    </div>
  );
};

export default DynamicActionConfigSchema;
