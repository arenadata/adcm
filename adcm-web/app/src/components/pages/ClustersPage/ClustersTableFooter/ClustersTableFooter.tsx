import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/clusters/clustersTableSlice';
import { Pagination, PaginationData } from '@uikit';

const ClustersTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.clusters.totalCount);
  const paginationParams = useStore((s) => s.adcm.clustersTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ClustersTableFooter;
