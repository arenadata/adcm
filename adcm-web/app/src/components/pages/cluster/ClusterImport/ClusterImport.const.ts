import type { ClusterImportsSetGroup, SelectedImportsGroup } from '@pages/cluster/ClusterImport/ClusterImport.types';

export const defaultLocalImports: SelectedImportsGroup = { clusters: new Map(), services: new Map() };
export const defaultSingleBindImports: ClusterImportsSetGroup = { clusters: new Set(), services: new Set() };
