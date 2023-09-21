import { useDispatch, useRequestTimer, useDebounce } from '@hooks';
import { defaultDebounceDelay } from '@constants';
import { useParams } from 'react-router-dom';
import { getHostProvider } from '@store/adcm/hostProviders/hostProviderSlice';

export const useRequestHostProviderPage = () => {
  const dispatch = useDispatch();
  const { hostproviderId: hostproviderIdFromUrl } = useParams();
  const hostproviderId = Number(hostproviderIdFromUrl);

  const debounceGetData = useDebounce(() => {
    if (!hostproviderId) return;
    dispatch(getHostProvider(hostproviderId));
  }, defaultDebounceDelay);

  const debounceRefreshData = useDebounce(() => {
    if (!hostproviderId) return;
    dispatch(getHostProvider(hostproviderId));
  }, defaultDebounceDelay);

  useRequestTimer(debounceGetData, debounceRefreshData, 0, []);
};
