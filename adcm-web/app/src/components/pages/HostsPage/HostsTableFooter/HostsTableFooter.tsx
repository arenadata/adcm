import { useDispatch, useStore } from '@hooks';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';
import { setPaginationParams } from '@store/adcm/hosts/hostsTableSlice';

const HostsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.hosts.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.hostsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default HostsTableFooter;
