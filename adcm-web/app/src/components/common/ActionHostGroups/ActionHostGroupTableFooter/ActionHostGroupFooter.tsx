import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { Pagination, PaginationData } from '@uikit';
import { setPaginationParams } from '@store/adcm/entityActionHostGroups/actionHostGroupsTableSlice';

const ActionHostGroupTableFooter: React.FC = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.actionHostGroups.totalCount);
  const paginationParams = useStore((s) => s.adcm.actionHostGroupsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ActionHostGroupTableFooter;
