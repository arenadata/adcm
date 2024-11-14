import React, { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter } from '@store/adcm/audit/auditOperations/auditOperationsTableSlice';
import { Button, LabeledField, Select, DatePicker } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import {
  objectTypeOptions,
  operationTypeOptions,
  operationResultOptions,
} from '@pages/audit/AuditOperationsPage/AuditOperationsTable/AuditOperations.constants';
import type { AdcmAuditOperationObjectType, AdcmAuditOperationResult, AdcmAuditOperationType } from '@models/adcm';

const AuditOperationsTableNotInputFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.auditOperationsTable.filter);

  const startDate = useMemo(() => new Date(filter.timeFrom), [filter.timeFrom]);
  const endDate = useMemo(() => new Date(filter.timeTo), [filter.timeTo]);

  const handleObjectTypeChange = (value: AdcmAuditOperationObjectType | null) => {
    dispatch(setFilter({ objectType: value ?? undefined }));
  };

  const handleOperationTypeChange = (value: AdcmAuditOperationType | null) => {
    dispatch(setFilter({ operationType: value ?? undefined }));
  };

  const handleResultChange = (value: AdcmAuditOperationResult | null) => {
    dispatch(setFilter({ operationResult: value ?? undefined }));
  };

  const handleTimeFrom = (newDate?: Date) => {
    if (!newDate) return;
    dispatch(setFilter({ timeFrom: newDate.getTime() }));
  };

  const handleTimeTo = (newDate?: Date) => {
    if (!newDate) return;
    dispatch(setFilter({ timeTo: newDate.getTime() }));
  };

  const handleResetFiltersClick = () => {
    dispatch(resetFilter());
  };

  return (
    <TableFilters>
      <LabeledField label="Object type" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.objectType ?? null}
          onChange={handleObjectTypeChange}
          options={objectTypeOptions}
          noneLabel="All"
        />
      </LabeledField>
      <LabeledField label="Operation type" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.operationType ?? null}
          onChange={handleOperationTypeChange}
          options={operationTypeOptions}
          noneLabel="All"
        />
      </LabeledField>
      <LabeledField label="Result" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.operationResult ?? null}
          onChange={handleResultChange}
          options={operationResultOptions}
          noneLabel="All"
        />
      </LabeledField>
      <LabeledField label="Time since" direction="row">
        <DatePicker value={startDate} onSubmit={handleTimeFrom} maxDate={endDate} />
      </LabeledField>
      <LabeledField label="to" direction="row">
        <DatePicker value={endDate} onSubmit={handleTimeTo} minDate={startDate} />
      </LabeledField>
      <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
    </TableFilters>
  );
};

export default AuditOperationsTableNotInputFilters;
