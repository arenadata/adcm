import { useDispatch, useStore } from '@hooks';
import { Pagination, PaginationData } from '@uikit';
import { setPaginationParams } from '@store/adcm/cluster/hosts/hostsTableSlice';

const ClusterHostsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.clusterHosts.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.clusterHostsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ClusterHostsTableFooter;
