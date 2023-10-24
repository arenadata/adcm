export enum NotificationVariant {
  Error = 'Error',
  Info = 'Info',
}

export interface BaseNotification<Model> {
  id: string;
  variant: NotificationVariant;
  ttl?: number; // in milliseconds
  model: Model;
}

export interface ErrorNotification extends BaseNotification<{ message: string }> {
  variant: NotificationVariant.Error;
}

export interface InfoNotification extends BaseNotification<{ message: string }> {
  variant: NotificationVariant.Info;
}

export type Notification = ErrorNotification | InfoNotification;
