import React, { useCallback, useState } from 'react';
import { ConfigurationFormContextContext } from './ConfigurationFormContext.context';
import { ConfigurationNodeFilter } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';

interface ConfigurationContextProviderProps {
  children: React.ReactNode;
}

const ConfigurationFormContextProvider: React.FC<ConfigurationContextProviderProps> = ({ children }) => {
  const [isValid, setIsValid] = useState(true);
  const [filter, setFilter] = useState<ConfigurationNodeFilter>({
    title: '',
    showAdvanced: false,
    showInvisible: false,
  });

  const handleFilterChange = useCallback(
    (changes: Partial<ConfigurationNodeFilter>) => {
      setFilter((prevFilter) => ({ ...prevFilter, ...changes }));
    },
    [setFilter],
  );

  const contextValue = {
    filter,
    onFilterChange: handleFilterChange,
    isValid,
    onChangeIsValid: setIsValid,
  };

  return (
    <ConfigurationFormContextContext.Provider value={contextValue}>{children}</ConfigurationFormContextContext.Provider>
  );
};

export default ConfigurationFormContextProvider;
