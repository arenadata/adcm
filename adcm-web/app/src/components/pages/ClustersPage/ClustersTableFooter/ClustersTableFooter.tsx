import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/clusters/clustersTableSlice';
import { Pagination, PaginationData } from '@uikit';

const ClustersTableFooter = () => {
  const dispatch = useDispatch();

  const {
    adcm: {
      clusters: { totalCount },
      clustersTable: { paginationParams },
    },
  } = useStore();

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ClustersTableFooter;
