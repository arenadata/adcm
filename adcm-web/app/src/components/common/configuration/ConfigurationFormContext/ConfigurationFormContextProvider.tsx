import React, { useCallback, useState } from 'react';
import { ConfigurationFormContextContext } from './ConfigurationFormContext.context';
import { ConfigurationTreeFilter } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';

interface ConfigurationContextProviderProps {
  children: React.ReactNode;
}

const ConfigurationFormContextProvider: React.FC<ConfigurationContextProviderProps> = ({ children }) => {
  const [isValid, setIsValid] = useState(true);
  const [filter, setFilter] = useState<ConfigurationTreeFilter>({
    title: '',
    showAdvanced: false,
    showInvisible: false,
  });
  const [areExpandedAll, setAreExpandedAll] = useState(false);

  const handleFilterChange = useCallback(
    (changes: Partial<ConfigurationTreeFilter>) => {
      setFilter((prevFilter) => ({ ...prevFilter, ...changes }));
    },
    [setFilter],
  );

  const handleChangeExpandedAll = useCallback(() => {
    setAreExpandedAll((prev) => !prev);
  }, [setAreExpandedAll]);

  const contextValue = {
    filter,
    onFilterChange: handleFilterChange,
    isValid,
    onChangeIsValid: setIsValid,
    areExpandedAll,
    handleChangeExpandedAll,
  };

  return (
    <ConfigurationFormContextContext.Provider value={contextValue}>{children}</ConfigurationFormContextContext.Provider>
  );
};

export default ConfigurationFormContextProvider;
