export enum LoadState {
  NotLoaded = 'notLoaded',
  Loading = 'loading',
  Loaded = 'loaded',
}

export enum RequestState {
  NotRequested = 'notRequested',
  Pending = 'pending',
  AccessDenied = 'accessDenied',
  NotFound = 'notFound',
  Completed = 'completed',
}

export type ActionState = 'not-started' | 'in-progress' | 'completed';
