import { configureStore, combineReducers } from '@reduxjs/toolkit';
import userSlice from '@store/userSlice';

// import notificationsSlice from '@store/notificationsSlice';

import { apiMiddleware } from './middlewares/apiMiddleware';

const rootReducer = combineReducers({
  user: userSlice,
  // notifications: notificationsSlice,
});

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(apiMiddleware),
});

export type StoreState = ReturnType<typeof rootReducer>;
export type AppDispatch = typeof store.dispatch;
