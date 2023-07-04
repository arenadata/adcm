import { store } from './store';
import type { AppDispatch } from './store';

export { store, AppDispatch };
export type StoreState = ReturnType<typeof store.getState>;
