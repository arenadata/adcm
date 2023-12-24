import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/bundles/bundlesTableSlice';
import { Pagination, PaginationData } from '@uikit';

const BundlesTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.bundles.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.bundlesTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default BundlesTableFooter;
