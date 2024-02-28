import { createSlice, PayloadAction, nanoid } from '@reduxjs/toolkit';
import {
  ErrorNotification,
  InfoNotification,
  Notification,
  NotificationVariant,
  SuccessNotification,
} from '@models/notification';

interface AlertOptions {
  id?: string;
  ttl?: number;
  message: string;
}

type NotificationsState = {
  notifications: Notification[];
};

const createInitialState = (): NotificationsState => ({
  notifications: [],
});

const notificationsSlice = createSlice({
  name: 'notifications',
  initialState: createInitialState(),
  reducers: {
    showError(state, action: PayloadAction<AlertOptions>) {
      const { ttl, id, message } = action.payload;

      const notification: ErrorNotification = {
        id: id ?? nanoid(),
        variant: NotificationVariant.Error,
        model: {
          message,
        },
        ttl: ttl ?? 5000,
      };
      state.notifications = [...state.notifications, notification];
    },
    showInfo(state, action: PayloadAction<AlertOptions>) {
      const { ttl, id, message } = action.payload;

      const notification: InfoNotification = {
        id: id ?? nanoid(),
        variant: NotificationVariant.Info,
        model: {
          message,
        },
        ttl: ttl ?? 5000,
      };
      state.notifications = [...state.notifications, notification];
    },
    showSuccess(state, action: PayloadAction<AlertOptions>) {
      const { ttl, id, message } = action.payload;

      const notification: SuccessNotification = {
        id: id ?? nanoid(),
        variant: NotificationVariant.Success,
        model: {
          message,
        },
        ttl: ttl ?? 5000,
      };
      state.notifications = [...state.notifications, notification];
    },
    closeNotification(state, action: PayloadAction<string>) {
      state.notifications = state.notifications.filter((n) => n.id !== action.payload);
    },
    cleanupNotifications() {
      return createInitialState();
    },
  },
});

export const { showInfo, showError, showSuccess, closeNotification, cleanupNotifications } = notificationsSlice.actions;
export default notificationsSlice.reducer;
