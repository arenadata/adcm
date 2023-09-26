import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/hostProviders/hostProvidersTableSlice';
import { Pagination, PaginationData } from '@uikit';

const HostProvidersTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.hostProviders.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.hostProvidersTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default HostProvidersTableFooter;
