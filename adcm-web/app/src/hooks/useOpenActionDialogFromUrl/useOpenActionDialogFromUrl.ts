import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { shallowEqual } from 'react-redux';
import { useDispatch, useStore } from '@hooks';
import { isBlockingConcernPresent } from '@utils/concernUtils';
import { searchParamActionId } from '@constants';
import type { EntityConfig, EntityParamsMap, EntityType } from './useOpenActionDialogFromUrl.types';
import type { AdcmDynamicAction } from '@models/adcm';

const EMPTY_ARRAY: AdcmDynamicAction[] = [];

export const useOpenActionDialogFromUrl = <T extends EntityType>(config: EntityConfig<T>): void => {
  const dispatch = useDispatch();
  const [searchParams] = useSearchParams();
  const entity = useStore(config.getEntity);
  const entityId = entity?.id;

  const dynamicActions = useStore((state) => (entityId ? config.getDynamicActions(state, entityId) : EMPTY_ARRAY));
  const additionalData = useStore(
    (state) => (config.getAdditionalData ? config.getAdditionalData(state) : undefined),
    shallowEqual,
  );

  useEffect(() => {
    const actionIdFromUrl = searchParams.get(searchParamActionId);
    if (
      !actionIdFromUrl ||
      !entity ||
      !entityId ||
      Number.isNaN(entityId) ||
      dynamicActions.length === 0 ||
      isBlockingConcernPresent(entity.concerns ?? [])
    ) {
      return;
    }

    const actionId = Number(actionIdFromUrl);

    if (Number.isNaN(actionId) || actionId <= 0) {
      return;
    }

    const foundAction = dynamicActions.find((a) => a.id === actionId);

    if (!foundAction) {
      return;
    }

    const entityParams = config.getEntityParams(entity, additionalData);

    if (!entityParams) {
      return;
    }

    const thunkAction = config.openDialog({
      ...entityParams,
      actionId,
    } as EntityParamsMap[T]);

    dispatch(thunkAction);
  }, [searchParams, entity, entityId, dynamicActions, additionalData, dispatch, config]);
};
