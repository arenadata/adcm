import { AdcmConfigGroup } from '@models/adcm';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { AppDispatch } from '@store';

interface MappedHostsToConfigGroupProps {
  configGroup: AdcmConfigGroup | null;
  mappedHostsIds: number[];
  appendHost: (configGroupId: number, hostId: number) => Promise<void>;
  removeHost: (configGroupId: number, hostId: number) => Promise<void>;
  dispatch: AppDispatch;
}

export const mappedHostsToConfigGroup = async ({
  configGroup,
  mappedHostsIds,
  appendHost,
  removeHost,
  dispatch,
}: MappedHostsToConfigGroupProps) => {
  if (!configGroup) {
    throw new Error('Something error');
  }

  const removeHostsIds = configGroup.hosts
    .filter((prevHost) => !mappedHostsIds.includes(prevHost.id))
    .map(({ id }) => id);

  const appendHostsIds = mappedHostsIds.filter((newHostId) => !configGroup.hosts.some(({ id }) => newHostId === id));

  const mappedProcessPromises = await Promise.allSettled([
    ...removeHostsIds.map(async (hostId) => await removeHost(configGroup.id, hostId)),
    ...appendHostsIds.map(async (hostId) => await appendHost(configGroup.id, hostId)),
  ]);

  const allRequestCount = removeHostsIds.length + appendHostsIds.length;
  const mappedSuccessRequest = fulfilledFilter(mappedProcessPromises);
  if (mappedSuccessRequest.length === 0 && allRequestCount > 0) {
    // throw exception because full crash
    throw new Error('All hosts can not mapped on this group');
  }

  if (mappedSuccessRequest.length < allRequestCount) {
    dispatch(showInfo({ message: 'Some hosts were successfully mapped on this group' }));
    dispatch(showError({ message: 'Some hosts can not mapped on this group' }));

    // return false because process done with partly success
    return false;
  }

  dispatch(showInfo({ message: 'All hosts were successfully mapped on this group' }));

  return true;
};
