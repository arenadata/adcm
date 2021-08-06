import { InjectionToken } from '@angular/core';
import { FormModel } from '@app/shared/add-component/add.service';

export const ADD_SERVICE_PROVIDER = new InjectionToken<IAddService>('AddService');


export interface IAddService {
  model(name?: string): FormModel
}
