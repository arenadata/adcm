/* eslint-disable @typescript-eslint/no-restricted-imports */
import type { TypedUseSelectorHook } from 'react-redux';
import { useSelector as useReduxSelector } from 'react-redux';
import type { AppStore } from '@store/store';

// Use instead of `useSelector` from 'react-redux
export const useStore: TypedUseSelectorHook<AppStore> = useReduxSelector;
