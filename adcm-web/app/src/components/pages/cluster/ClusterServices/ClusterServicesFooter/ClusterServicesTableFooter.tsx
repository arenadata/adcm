import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/cluster/services/servicesTableSlice';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';

const ClusterServicesTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.services.totalCount);
  const paginationParams = useStore((s) => s.adcm.servicesTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ClusterServicesTableFooter;
