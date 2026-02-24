import type React from 'react';
import { useState } from 'react';
import { SubJobsLogsAutoScrollContext, type SubJobsLogsAutoScrollOptions } from './SubJobLogsAutoScroll.context';

export interface SubJobLogsAutoScrollProviderProps extends React.PropsWithChildren {
  isInitialAutoScroll: boolean;
}

const SubJobLogsAutoScrollProvider = ({ isInitialAutoScroll, children }: SubJobLogsAutoScrollProviderProps) => {
  const [isAutoScroll, setIsAutoScroll] = useState(isInitialAutoScroll);

  const contextValue: SubJobsLogsAutoScrollOptions = {
    isAutoScroll,
    toggleAutoScroll: setIsAutoScroll,
  };

  return <SubJobsLogsAutoScrollContext.Provider value={contextValue}>{children}</SubJobsLogsAutoScrollContext.Provider>;
};

export default SubJobLogsAutoScrollProvider;
