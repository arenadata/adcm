import { createAction, props } from '@ngrx/store';

export type TypeName =
  | 'bundle'
  | 'cluster'
  | 'host'
  | 'provider'
  | 'service'
  | 'job'
  | 'task'
  | 'user'
  | 'profile'
  | 'adcm'
  | 'stats'
  | 'hostcomponent'
  | 'component';

export interface IEMObject {
  type: TypeName;
  id: number;
  details: {
    id?: string;
    type: string;
    value: any;
  };
}

export interface EventMessage {
  event:
    | 'add'
    | 'add_job_log'
    | 'create'
    | 'delete'
    | 'remove'
    | 'change_config'
    | 'change_state'
    | 'change_status'
    | 'change_job_status'
    | 'change_hostcomponentmap'
    | 'raise_issue'
    | 'clear_issue'
    | 'upgrade';
  object?: IEMObject;
}

export enum StatusType {
  Open = 'open',
  Close = 'close',
  Lost = 'lost',
}

export const socketInit = createAction('[Socket] Init');
export const socketOpen = createAction('[Socket] Open', props<{ status: StatusType }>());
export const socketClose = createAction('[Socket] Close', props<{ status: StatusType }>());
export const socketLost = createAction('[Socket] Lost', props<{ status: StatusType }>());
export const socketResponse = createAction('[Socket] Response', props<{ message: EventMessage }>());
