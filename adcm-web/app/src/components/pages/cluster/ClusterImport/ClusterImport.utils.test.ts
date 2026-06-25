import type { AdcmClusterImport, AdcmClusterImportService } from '@models/adcm';
import { AdcmClusterImportPayloadType, AdcmClusterStatus } from '@models/adcm';
import type { ClusterImportsSetGroup, SelectedImportsGroup } from './ClusterImport.types';
import {
  formatServiceToggleData,
  getCheckServiceList,
  getClusterImportCardState,
  getUncheckServiceList,
  hasPrototypeSelected,
  isServiceBlockedBySingleBind,
  isServiceSelected,
  prepToggleSelectedImportsData,
  prepToggleSelectedSingleBindData,
} from './ClusterImport.utils';

const createService = (
  id: number,
  prototypeName: string,
  options: Partial<AdcmClusterImportService> = {},
): AdcmClusterImportService => ({
  id,
  name: prototypeName,
  displayName: prototypeName,
  version: '1.0',
  isRequired: false,
  isMultiBind: false,
  prototype: {
    id,
    name: prototypeName,
    displayName: prototypeName,
    version: '1.0',
  },
  ...options,
});

const createClusterImport = (
  clusterId: number,
  services: AdcmClusterImportService[],
  importCluster: AdcmClusterImport['importCluster'] = null,
): AdcmClusterImport => ({
  cluster: {
    id: clusterId,
    name: `cluster-${clusterId}`,
    status: AdcmClusterStatus.Up,
    state: 'installed',
  },
  importCluster,
  importServices: services,
  binds: [],
});

const emptyImports = (): SelectedImportsGroup => ({
  clusters: new Map(),
  services: new Map(),
});

const emptySingleBind = (): ClusterImportsSetGroup => ({
  clusters: new Set(),
  services: new Set(),
});

const selectService = (selectedImports: SelectedImportsGroup, service: AdcmClusterImportService) => {
  selectedImports.services.set(service.id, {
    id: service.id,
    type: AdcmClusterImportPayloadType.Service,
    prototypeName: service.prototype.name,
  });
};

describe('isServiceSelected', () => {
  it('returns true when service id is in selectedImports', () => {
    const service = createService(1, 'adpg_control');
    const selectedImports = emptyImports();
    selectService(selectedImports, service);

    expect(isServiceSelected(service, selectedImports)).toBe(true);
  });

  it('returns false when service id is not in selectedImports', () => {
    const service = createService(1, 'adpg_control');

    expect(isServiceSelected(service, emptyImports())).toBe(false);
  });
});

describe('isServiceBlockedBySingleBind', () => {
  it('returns false for multi-bind services', () => {
    const service = createService(1, 'adpg_control', { isMultiBind: true });
    const selectedSingleBind = emptySingleBind();
    selectedSingleBind.services.add('adpg_control');

    expect(isServiceBlockedBySingleBind(service, emptyImports(), selectedSingleBind)).toBe(false);
  });

  it('returns true when single-bind prototype is taken in another cluster', () => {
    const service = createService(2, 'ad_eureka');
    const selectedSingleBind = emptySingleBind();
    selectedSingleBind.services.add('ad_eureka');

    expect(isServiceBlockedBySingleBind(service, emptyImports(), selectedSingleBind)).toBe(true);
  });

  it('returns false when single-bind service is selected in current cluster', () => {
    const service = createService(2, 'ad_eureka');
    const selectedImports = emptyImports();
    const selectedSingleBind = emptySingleBind();

    selectService(selectedImports, service);
    selectedSingleBind.services.add('ad_eureka');

    expect(isServiceBlockedBySingleBind(service, selectedImports, selectedSingleBind)).toBe(false);
  });
});

describe('hasPrototypeSelected', () => {
  it('returns true when prototype exists in map values', () => {
    const items = new Map([[1, { id: 1, type: AdcmClusterImportPayloadType.Service, prototypeName: 'adpg_control' }]]);

    expect(hasPrototypeSelected(items, 'adpg_control')).toBe(true);
    expect(hasPrototypeSelected(items, 'ad_eureka')).toBe(false);
  });
});

describe('getClusterImportCardState', () => {
  const controlService1 = createService(101, 'adpg_control');
  const postgresService1 = createService(102, 'postgres');
  const eurekaService1 = createService(103, 'ad_eureka');

  const controlService2 = createService(201, 'adpg_control');
  const postgresService2 = createService(202, 'postgres');
  const eurekaService2 = createService(203, 'ad_eureka');

  const controlCluster1 = createClusterImport(1, [controlService1, postgresService1, eurekaService1]);
  const controlCluster2 = createClusterImport(2, [controlService2, postgresService2, eurekaService2]);

  it('does not mark All Services selected when services are chosen in different clusters', () => {
    const selectedImports = emptyImports();
    const selectedSingleBind = emptySingleBind();

    selectService(selectedImports, controlService1);
    selectService(selectedImports, eurekaService2);
    selectedSingleBind.services.add('adpg_control');
    selectedSingleBind.services.add('ad_eureka');

    const cluster1State = getClusterImportCardState(controlCluster1, selectedImports, selectedSingleBind);
    const cluster2State = getClusterImportCardState(controlCluster2, selectedImports, selectedSingleBind);

    expect(cluster1State.isAllServicesSelected).toBe(false);
    expect(cluster2State.isAllServicesSelected).toBe(false);
    expect(cluster1State.isAnyServiceSelected).toBe(true);
    expect(cluster2State.isAnyServiceSelected).toBe(true);
    expect(cluster1State.isAllServicesDisabled).toBe(true);
    expect(cluster2State.isAllServicesDisabled).toBe(true);
  });

  it('disables All Services when any service is blocked in another cluster', () => {
    const adpgControl1 = createService(101, 'adpg_control');
    const adEureka1 = createService(103, 'ad_eureka');
    const adpgControl2 = createService(201, 'adpg_control');
    const adEureka2 = createService(203, 'ad_eureka');

    const cluster1 = createClusterImport(1, [adpgControl1, adEureka1]);
    const cluster2 = createClusterImport(2, [adpgControl2, adEureka2]);

    const selectedImports = emptyImports();
    const selectedSingleBind = emptySingleBind();

    selectService(selectedImports, adpgControl1);
    selectService(selectedImports, adEureka2);
    selectedSingleBind.services.add('adpg_control');
    selectedSingleBind.services.add('ad_eureka');

    const cluster1State = getClusterImportCardState(cluster1, selectedImports, selectedSingleBind);
    const cluster2State = getClusterImportCardState(cluster2, selectedImports, selectedSingleBind);

    expect(cluster1State.isAllServicesDisabled).toBe(true);
    expect(cluster2State.isAllServicesDisabled).toBe(true);
  });

  it('marks All Services selected only for cluster with all sub-checkboxes selected', () => {
    const selectedImports = emptyImports();
    const selectedSingleBind = emptySingleBind();

    selectService(selectedImports, controlService2);
    selectService(selectedImports, postgresService2);
    selectService(selectedImports, eurekaService2);
    selectedSingleBind.services.add('adpg_control');
    selectedSingleBind.services.add('postgres');
    selectedSingleBind.services.add('ad_eureka');

    const cluster1State = getClusterImportCardState(controlCluster1, selectedImports, selectedSingleBind);
    const cluster2State = getClusterImportCardState(controlCluster2, selectedImports, selectedSingleBind);

    expect(cluster1State.isAllServicesSelected).toBe(false);
    expect(cluster1State.isAllServicesDisabled).toBe(true);
    expect(cluster2State.isAllServicesSelected).toBe(true);
    expect(cluster2State.isAllServicesDisabled).toBe(false);
  });

  it('marks All Services selected when every service of the same cluster is selected', () => {
    const selectedImports = emptyImports();
    const selectedSingleBind = emptySingleBind();

    selectService(selectedImports, controlService1);
    selectService(selectedImports, postgresService1);
    selectService(selectedImports, eurekaService1);

    const state = getClusterImportCardState(controlCluster1, selectedImports, selectedSingleBind);

    expect(state.isAllServicesSelected).toBe(true);
    expect(state.isAnyServiceSelected).toBe(true);
    expect(state.isAllServicesDisabled).toBe(false);
  });

  it('returns required services that are not selected by prototype', () => {
    const requiredService = createService(301, 'required_service', { isRequired: true });
    const clusterImport = createClusterImport(3, [requiredService]);
    const selectedImports = emptyImports();

    const state = getClusterImportCardState(clusterImport, selectedImports, emptySingleBind());

    expect(state.requiredServiceImport).toEqual([requiredService]);
  });

  it('disables cluster import when single-bind cluster prototype is already taken', () => {
    const importCluster = {
      id: 10,
      isRequired: false,
      isMultiBind: false,
      prototype: {
        id: 10,
        name: 'adpg_control_cluster',
        displayName: 'ADPG Control',
        version: '1.0',
      },
    };
    const clusterImport = createClusterImport(4, [], importCluster);
    const selectedSingleBind = emptySingleBind();
    selectedSingleBind.clusters.add('adpg_control_cluster');

    const state = getClusterImportCardState(clusterImport, emptyImports(), selectedSingleBind);

    expect(state.isClusterImportDisabled).toBe(true);
    expect(state.isClusterSelected).toBe(false);
  });
});

describe('getCheckServiceList', () => {
  it('skips services blocked by single-bind in another cluster', () => {
    const availableService = createService(1, 'postgres', { isMultiBind: true });
    const blockedService = createService(2, 'ad_eureka');
    const selectedSingleBind = emptySingleBind();
    selectedSingleBind.services.add('ad_eureka');

    const result = getCheckServiceList({
      services: [availableService, blockedService],
      selectedImports: emptyImports(),
      selectedSingleBind,
    });

    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(availableService.id);
  });

  it('skips already selected services', () => {
    const selectedService = createService(1, 'adpg_control');
    const unselectedService = createService(2, 'postgres');
    const selectedImports = emptyImports();
    selectService(selectedImports, selectedService);

    const result = getCheckServiceList({
      services: [selectedService, unselectedService],
      selectedImports,
      selectedSingleBind: emptySingleBind(),
    });

    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(unselectedService.id);
  });
});

describe('getUncheckServiceList', () => {
  it('returns only selected services of the cluster', () => {
    const selectedService = createService(1, 'adpg_control');
    const unselectedService = createService(2, 'postgres');
    const selectedImports = emptyImports();
    selectService(selectedImports, selectedService);

    const result = getUncheckServiceList({
      services: [selectedService, unselectedService],
      selectedImports,
      selectedSingleBind: emptySingleBind(),
    });

    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(selectedService.id);
  });
});

describe('toggle handlers integration', () => {
  it('selects and unselects service via prepToggle helpers', () => {
    const service = createService(1, 'adpg_control');
    let selectedImports = emptyImports();
    let selectedSingleBind = emptySingleBind();

    selectedImports = prepToggleSelectedImportsData(selectedImports, [formatServiceToggleData(service)]);
    selectedSingleBind = prepToggleSelectedSingleBindData(selectedSingleBind, [formatServiceToggleData(service)]);

    expect(isServiceSelected(service, selectedImports)).toBe(true);
    expect(selectedSingleBind.services.has('adpg_control')).toBe(true);

    selectedImports = prepToggleSelectedImportsData(selectedImports, [formatServiceToggleData(service)]);
    selectedSingleBind = prepToggleSelectedSingleBindData(selectedSingleBind, [formatServiceToggleData(service)]);

    expect(isServiceSelected(service, selectedImports)).toBe(false);
    expect(selectedSingleBind.services.has('adpg_control')).toBe(false);
  });
});
