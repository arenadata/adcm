import type React from 'react';
import { useMemo } from 'react';
import { useStore, useDispatch } from '@hooks';
import { setFilter, resetFilter } from '@store/adcm/audit/auditLogins/auditLoginsTableSlice';
import { Button, LabeledField, Select, DatePicker, SearchInput, ButtonGroup } from '@uikit';
import TableFilters from '@commonComponents/Table/TableFilters/TableFilters';
import { loginsResultOptions } from '@pages/audit/AuditLoginsPage/AuditLoginsTable/AuditLoginsTable.constants';
import type { AdcmAuditLoginResultType } from '@models/adcm';

const AuditLoginsTableFilters = () => {
  const dispatch = useDispatch();

  const filter = useStore(({ adcm }) => adcm.auditLoginsTable.filter);

  const startDate = useMemo(() => new Date(filter.timeFrom), [filter.timeFrom]);
  const endDate = useMemo(() => new Date(filter.timeTo), [filter.timeTo]);

  const handleUsernameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    dispatch(setFilter({ login: event.target.value }));
  };

  const handleLoginResultChange = (value: AdcmAuditLoginResultType | null) => {
    dispatch(setFilter({ loginResult: value ?? undefined }));
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
      <SearchInput
        placeholder="Search login"
        value={filter.login || ''}
        variant="primary"
        onChange={handleUsernameChange}
      />
      <LabeledField label="Result" direction="row">
        <Select
          maxHeight={200}
          placeholder="All"
          value={filter.loginResult ?? null}
          onChange={handleLoginResultChange}
          options={loginsResultOptions}
          noneLabel="All"
        />
      </LabeledField>
      <LabeledField label="Time since" direction="row">
        <DatePicker value={startDate} onSubmit={handleTimeFrom} maxDate={endDate} />
      </LabeledField>
      <LabeledField label="to" direction="row">
        <DatePicker value={endDate} onSubmit={handleTimeTo} minDate={startDate} />
      </LabeledField>
      <ButtonGroup>
        <Button variant="tertiary" iconLeft="g1-return" onClick={handleResetFiltersClick} />
      </ButtonGroup>
    </TableFilters>
  );
};

export default AuditLoginsTableFilters;
