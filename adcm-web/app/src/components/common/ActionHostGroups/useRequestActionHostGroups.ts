import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { useEffect } from 'react';
import { getActionHostGroups, cleanupActionHostGroups } from '@store/adcm/entityActionHostGroups/actionHostGroupsSlice';
import { cleanupActions } from '@store/adcm/entityActionHostGroups/actionHostGroupsActionsSlice';
import { cleanupList } from '@store/adcm/entityActionHostGroups/actionHostGroupsTableSlice';
import { cleanupDynamicActions, loadDynamicActions } from '@store/adcm/entityDynamicActions/dynamicActionsSlice';
import { cleanupDynamicActionsMapping } from '@store/adcm/entityDynamicActions/dynamicActionsMappingSlice';
import { defaultDebounceDelay } from '@constants';
import type { ActionHostGroupOwner, EntityArgs } from '@store/adcm/entityActionHostGroups/actionHostGroups.types';

export const useRequestActionHostGroups = <T extends ActionHostGroupOwner>(
  entityType: T,
  entityArgs: EntityArgs<T>,
) => {
  const dispatch = useDispatch();

  const actionHostGroups = useStore(({ adcm }) => adcm.actionHostGroups.actionHostGroups);
  const filter = useStore(({ adcm }) => adcm.actionHostGroupsTable.filter);
  const paginationParams = useStore(({ adcm }) => adcm.actionHostGroupsTable.paginationParams);

  useEffect(() => {
    if (actionHostGroups.length) {
      const actionHostGroupIds = actionHostGroups.map(({ id }) => id);
      dispatch(loadDynamicActions({ entityType, entityArgs, actionHostGroupIds }));
    }
  }, [dispatch, entityType, entityArgs, actionHostGroups]);

  useEffect(() => {
    return () => {
      dispatch(cleanupActionHostGroups());
      dispatch(cleanupActions());
      dispatch(cleanupList());
      dispatch(cleanupDynamicActions());
      dispatch(cleanupDynamicActionsMapping());
    };
  }, [dispatch]);

  const debounceGetClusterActionHostGroups = useDebounce(() => {
    dispatch(getActionHostGroups({ entityType, entityArgs }));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterActionHostGroups, () => {}, 0, [entityArgs, filter, paginationParams]);
};
