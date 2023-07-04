import { useSelector as useReduxSelector } from 'react-redux';
import { StoreState } from '@store';

export const useStore = () => {
  return useReduxSelector((state: StoreState) => state);
};
