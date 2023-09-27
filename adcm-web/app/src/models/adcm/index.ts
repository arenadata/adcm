export * from './cluster';
export * from './host';
export * from './prototype';
export * from './clusterMapping';
export * from './concern';
export * from './hostProvider';
export * from './service';
export * from './maintenanceMode';
export * from './users';
export * from './group';
export * from './audit';
export * from './configuration';
export * from './jobs';
export * from './policy';
export * from './clusterImports';
export * from './clusterOverview';
export * from './roles';
export * from './clusterServiceComponent';
export * from './clusterHosts';
export * from './profile';
export * from './license';
export * from './dynamicAction';

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
