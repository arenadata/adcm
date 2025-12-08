import type React from 'react';
import s from './ConfigurationEmptyState.module.scss';

const ConfigurationEmptyState: React.FC = () => {
  return (
    <div className={s.configurationEmptyState}>
      <span>The object has no configuration</span>
    </div>
  );
};

export default ConfigurationEmptyState;
