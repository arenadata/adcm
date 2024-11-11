import { useDispatch, useStore } from '@hooks';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';
import { setPaginationParams } from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupsTableSlice';

const HostProviderConfigurationGroupTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.hostProviderConfigGroups.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.hostProviderConfigGroupsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default HostProviderConfigurationGroupTableFooter;
