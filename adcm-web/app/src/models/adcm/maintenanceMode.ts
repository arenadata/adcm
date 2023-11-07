export enum AdcmMaintenanceMode {
  Off = 'off',
  On = 'on',
  Pending = 'pending',
  Changing = 'changing',
}

export interface AdcmSetMaintenanceModeResponse {
  maintenanceMode: AdcmMaintenanceMode;
}
