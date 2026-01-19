import type { AdcmDynamicAction } from '@models/adcm/dynamicAction';
import type { AdcmCluster, AdcmService, AdcmServiceComponent, AdcmHostProvider } from '@models/adcm';
import type { RootState, AppDispatch } from '@store/store';

export type EntityType = 'cluster' | 'service' | 'component' | 'hostProvider';

export type EntityTypeMap = {
  cluster: AdcmCluster;
  service: AdcmService;
  component: AdcmServiceComponent;
  hostProvider: AdcmHostProvider;
};

export type EntityParamsMap = {
  cluster: { cluster: AdcmCluster; actionId: number };
  service: { cluster: AdcmCluster; service: AdcmService; actionId: number };
  component: { component: AdcmServiceComponent; actionId: number };
  hostProvider: { hostProvider: AdcmHostProvider; actionId: number };
};

export type AdditionalDataMap = {
  cluster: never;
  service: { cluster: AdcmCluster | undefined };
  component: never;
  hostProvider: never;
};

export type OpenDialogAction<T extends EntityType> = (params: EntityParamsMap[T]) => Parameters<AppDispatch>[0];

export interface EntityConfig<T extends EntityType> {
  getEntity: (store: RootState) => EntityTypeMap[T] | null | undefined;
  getDynamicActions: (store: RootState, entityId: number) => AdcmDynamicAction[];
  openDialog: OpenDialogAction<T>;
  getAdditionalData?: (store: RootState) => AdditionalDataMap[T];
  getEntityParams: (
    entity: EntityTypeMap[T],
    additionalData?: AdditionalDataMap[T],
  ) => Omit<EntityParamsMap[T], 'actionId'> | undefined;
}
