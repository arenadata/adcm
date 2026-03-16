import { useContext, type Context } from 'react';
import { createContextHelper } from '@hooks/useContextHelper';

export interface SubJobsLogsAutoScrollOptions {
  isAutoScroll: boolean;
  toggleAutoScroll: (isAutoScroll: boolean) => void;
}

export const SubJobsLogsAutoScrollContext =
  createContextHelper<SubJobsLogsAutoScrollOptions>('SubJobsLogsAutoScrollContext');

export const useSubJobsLogsAutoScrollContext = () => {
  const contextValue = useContext<SubJobsLogsAutoScrollOptions | undefined>(
    SubJobsLogsAutoScrollContext as Context<SubJobsLogsAutoScrollOptions | undefined>,
  );

  if (!contextValue) {
    console.warn(`Context ${SubJobsLogsAutoScrollContext.displayName} not found, autoscroll is not available`);
  }

  return contextValue;
};
