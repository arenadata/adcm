import { useDispatch, useStore } from '@hooks';
import { Pagination, PaginationData } from '@uikit';
import { setPaginationParams } from '@store/adcm/cluster/configGroups/clusterConfigGroupsTableSlice';

const ClusterConfigGroupTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.clusterConfigGroups.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.clusterConfigGroupsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ClusterConfigGroupTableFooter;
