import { PaginationParams } from '@models/table';

export interface AdcmSchemaConfigCellActionsList {
  id: number;
  displayName: string;
}

export interface AdcmSchemaConfig {
  id: number;
  isCurrent: boolean;
  creationTime: string;
  description: string;
}

export interface ConfigVersionPanelProps {
  paginationParams: PaginationParams;
  configCellActionsList: AdcmSchemaConfigCellActionsList[];
  configs: AdcmSchemaConfig[];
  onChangePage: (arg: PaginationParams) => void;
  onSelectCell: (arg: number) => void;
  onSelectCellAction: () => void;
}
