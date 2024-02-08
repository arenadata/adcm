// eslint-disable-next-line @typescript-eslint/no-restricted-imports
import { useDispatch as useReduxDispatch } from 'react-redux';
import type { AppDispatch } from '@store/store';

// Use throughout your app instead of plain `useDispatch` and `useSelector`
type Dispatch = () => AppDispatch;
export const useDispatch: Dispatch = useReduxDispatch;
