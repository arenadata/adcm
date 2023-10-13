import React from 'react';
import Panel from '@uikit/Panel/Panel';
import { Button } from '@uikit';
import s from './ConfigGroupsHeader.module.scss';

interface ConfigGroupsHeaderProps {
  onCreate: () => void;
}

const ConfigGroupsHeader: React.FC<ConfigGroupsHeaderProps> = ({ onCreate }) => {
  return (
    <Panel className={s.configGroupsHeader}>
      <div>
        Configuration group can be applied to hosts on top of <strong>Primary configuration</strong>
      </div>
      <Button onClick={onCreate}>Create config group</Button>
    </Panel>
  );
};

export default ConfigGroupsHeader;
