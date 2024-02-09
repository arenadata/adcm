export interface Batch<T> {
  results: T[];
  count: number;
  // next: string | null; // contains url for the next page (e.g. "http://localhost:8000/api/v2/clusters/?limit=10&offset=10")
  // previous: string | null; // contains url for the prev page (e.g. see example above)
}

export interface AdcmError {
  code: string;
  desc: string;
  // level: string;
}

export interface AdcmRenameArgs {
  id: number;
  name: string;
}

export enum AdcmEntitySystemState {
  Created = 'created',
}

export type AdcmEntityState = AdcmEntitySystemState.Created | string;
