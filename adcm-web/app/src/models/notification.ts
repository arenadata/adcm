export enum NotificationVariant {
  Error = 'Error',
  Info = 'Info',
  Success = 'Success',
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

export interface SuccessNotification extends BaseNotification<{ message: string }> {
  variant: NotificationVariant.Success;
}

export type Notification = ErrorNotification | InfoNotification | SuccessNotification;
