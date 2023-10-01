import {
  AdcmSchemaConfig,
  AdcmSchemaConfigCellActionsList,
} from '@commonComponents/ConfigVersionPanel/ConfigVersionPanel.types';

export interface ConfigVersionCellProps {
  configCellActionsList: AdcmSchemaConfigCellActionsList[];
  cellInfo: AdcmSchemaConfig;
  onClick: (cellId: number) => void;
  onSelectCellAction: (actionId: number) => void;
}
