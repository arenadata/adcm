import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { getHostProvider } from '@store/adcm/hostProviders/hostProviderSlice';
import { loadHostProvidersDynamicActions } from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';

export const useRequestHostProviderPage = () => {
  const dispatch = useDispatch();
  const { hostproviderId: hostproviderIdFromUrl } = useParams();
  const hostproviderId = Number(hostproviderIdFromUrl);

  const debounceGetData = useDebounce(() => {
    if (!hostproviderId) return;
    dispatch(getHostProvider(hostproviderId))
      .unwrap()
      .then((provider) => {
        dispatch(loadHostProvidersDynamicActions([provider]));
      });
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!hostproviderId) return;
    dispatch(getHostProvider(hostproviderId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, []);
};
