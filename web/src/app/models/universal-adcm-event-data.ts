export interface UniversalAdcmEventData<T> {
  event: MouseEvent;
  action: 'getNextPageCluster' | 'getClusters' | 'addCluster';
  row: T;
}
