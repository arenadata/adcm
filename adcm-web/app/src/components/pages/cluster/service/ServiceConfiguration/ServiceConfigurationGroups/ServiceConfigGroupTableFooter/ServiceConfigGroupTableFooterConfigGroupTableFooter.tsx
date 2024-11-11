import { useDispatch, useStore } from '@hooks';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';
import { setPaginationParams } from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsTableSlice';

const ServiceConfigGroupTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.serviceConfigGroups.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.serviceConfigGroupsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ServiceConfigGroupTableFooter;
