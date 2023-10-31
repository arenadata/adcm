import { useSelector as useReduxSelector } from 'react-redux';
import { StoreState } from '@store';

type Selector<Selected> = (state: StoreState) => Selected;

export const useStore = <Selected>(selector: Selector<Selected>) => {
  return useReduxSelector<StoreState, Selected>(selector);
};
