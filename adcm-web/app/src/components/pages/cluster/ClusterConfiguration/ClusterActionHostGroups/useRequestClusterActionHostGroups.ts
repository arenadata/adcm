import { useDebounce, useDispatch, useRequestTimer } from '@hooks';
import { useEffect } from 'react';
import {
  getClusterActionHostGroups,
  cleanupClusterActionHostGroups,
} from '@store/adcm/entityActionHostGroups/actionHostGroupsSlice';
import { useParams } from 'react-router-dom';
import { defaultDebounceDelay } from '@constants';

export const useRequestClusterActionHostGroups = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  useEffect(() => {
    return () => {
      dispatch(cleanupClusterActionHostGroups());
    };
  }, [dispatch]);

  const debounceGetClusterActionHostGroups = useDebounce(() => {
    if (clusterId) {
      dispatch(getClusterActionHostGroups({ clusterId }));
    }
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetClusterActionHostGroups, () => {}, 0, [clusterId]);
};
