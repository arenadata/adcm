import type React from 'react';
import SyncScrollContextProvider from './SyncScrollContextProvider';

export type SyncScrollProps = React.PropsWithChildren;

const SyncScroll = ({ children }: SyncScrollProps) => {
  return <SyncScrollContextProvider>{children}</SyncScrollContextProvider>;
};

export default SyncScroll;
