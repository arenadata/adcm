import { AdcmClusterImportPostItem, AdcmClusterImportService } from '@models/adcm';

export interface SelectedImportItem extends AdcmClusterImportPostItem {
  name: string;
}

export interface SelectedImportHandlerData extends SelectedImportItem {
  isMultiBind: boolean;
}

export interface SelectedImportsGroup {
  clusters: Map<number, SelectedImportItem>;
  services: Map<number, SelectedImportItem>;
}

export interface ClusterImportsSetGroup {
  clusters: Set<string>;
  services: Set<string>;
}

export interface ClusterImportCardServiceItemProps {
  selectedImports: SelectedImportsGroup;
  selectedSingleBind: ClusterImportsSetGroup;
  service: AdcmClusterImportService;
  onCheckHandler: (selectedImport: SelectedImportHandlerData[]) => void;
}

export type PrepServicesList = Omit<ClusterImportCardServiceItemProps, 'onCheckHandler' | 'service'> & {
  services: AdcmClusterImportService[];
};
