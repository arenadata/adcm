import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsTableSlice';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';

const ServiceComponentsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.serviceComponents.totalCount);
  const paginationParams = useStore((s) => s.adcm.serviceComponentsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ServiceComponentsTableFooter;
