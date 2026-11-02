/* eslint-disable spellcheck/spell-checker */
import {
  AdcmMaintenanceMode,
  AdcmPrototypeType,
  AdcmLicenseStatus,
  type AdcmHostShortView,
  type AdcmMapping,
  type AdcmMappingComponent,
  type AdcmMappingComponentService,
  type AdcmServicePrototype,
} from '@models/adcm';

const prototype = (id: number, name: string, displayName: string) => ({
  id,
  name,
  displayName,
  version: '1.0',
});

export const hostAlpha: AdcmHostShortView = {
  id: 1,
  name: 'alpha',
  isMaintenanceModeAvailable: true,
  maintenanceMode: AdcmMaintenanceMode.Off,
};

export const hostBeta: AdcmHostShortView = {
  id: 2,
  name: 'beta',
  isMaintenanceModeAvailable: true,
  maintenanceMode: AdcmMaintenanceMode.Off,
};

export const hostGamma: AdcmHostShortView = {
  id: 3,
  name: 'gamma',
  isMaintenanceModeAvailable: true,
  maintenanceMode: AdcmMaintenanceMode.On,
};

export const hosts: AdcmHostShortView[] = [hostAlpha, hostBeta, hostGamma];

export const serviceZookeeper: AdcmMappingComponentService = {
  id: 10,
  name: 'zookeeper',
  displayName: 'Zookeeper',
  state: 'created',
  prototype: prototype(19, 'zookeeper', 'Zookeeper'),
};

export const serviceHbase: AdcmMappingComponentService = {
  id: 20,
  name: 'hbase',
  displayName: 'HBase',
  state: 'installed',
  prototype: prototype(6, 'hbase', 'HBase'),
};

export const createStoryPrototype = prototype;

export const createStoryHost = (
  id: number,
  name: string,
  maintenanceMode: AdcmMaintenanceMode = AdcmMaintenanceMode.Off,
): AdcmHostShortView => ({
  id,
  name,
  isMaintenanceModeAvailable: true,
  maintenanceMode,
});

export const createStoryService = (
  id: number,
  name: string,
  displayName: string,
  state: AdcmMappingComponentService['state'] = 'created',
): AdcmMappingComponentService => ({
  id,
  name,
  displayName,
  state,
  prototype: prototype(id + 5000, name, displayName),
});

export const createStoryComponent = (
  id: number,
  name: string,
  displayName: string,
  service: AdcmMappingComponentService,
  constraints: AdcmMappingComponent['constraints'],
  dependOn: AdcmMappingComponent['dependOn'] = null,
): AdcmMappingComponent => ({
  id,
  name,
  displayName,
  isMaintenanceModeAvailable: true,
  maintenanceMode: AdcmMaintenanceMode.Off,
  constraints,
  service,
  prototype: prototype(id + 1000, name, displayName),
  dependOn,
});

export const zkServer: AdcmMappingComponent = createStoryComponent(101, 'zk_server', 'ZK Server', serviceZookeeper, [
  'odd',
]);

export const zkClient: AdcmMappingComponent = createStoryComponent(102, 'zk_client', 'ZK Client', serviceZookeeper, [
  0,
  '+',
]);

export const hbaseMaster: AdcmMappingComponent = createStoryComponent(
  201,
  'hbase_master',
  'HBase Master',
  serviceHbase,
  [1, '+'],
);

export const hbaseClient: AdcmMappingComponent = createStoryComponent(
  202,
  'hbase_client',
  'HBase Client',
  serviceHbase,
  [0, '+'],
);

export const components: AdcmMappingComponent[] = [zkServer, zkClient, hbaseMaster, hbaseClient];

export const pairsAlphaZkServer: AdcmMapping[] = [{ hostId: hostAlpha.id, componentId: zkServer.id }];

export const hdfsServicePrototype: AdcmServicePrototype = {
  id: 90,
  name: 'hdfs',
  displayName: 'HDFS',
  version: '1.0',
  type: AdcmPrototypeType.Service,
  license: {
    status: AdcmLicenseStatus.Unaccepted,
    text: 'HDFS license agreement text',
  },
  isRequired: false,
  dependOn: null,
};

export const zkServerDependingOnHdfs: AdcmMappingComponent = {
  ...zkServer,
  dependOn: [
    {
      servicePrototype: {
        id: hdfsServicePrototype.id,
        name: hdfsServicePrototype.name,
        displayName: hdfsServicePrototype.displayName,
        version: hdfsServicePrototype.version,
        license: hdfsServicePrototype.license,
        componentPrototypes: [prototype(91, 'namenode', 'NameNode')],
      },
    },
  ],
};

export const zkClientDependingOnZkServer: AdcmMappingComponent = {
  ...zkClient,
  dependOn: [
    {
      servicePrototype: {
        id: serviceZookeeper.prototype.id,
        name: serviceZookeeper.name,
        displayName: serviceZookeeper.displayName,
        version: serviceZookeeper.prototype.version,
        license: { status: AdcmLicenseStatus.Absent, text: null },
        componentPrototypes: [zkServer.prototype],
      },
    },
  ],
};

export const withConstraints = (
  component: AdcmMappingComponent,
  constraints: AdcmMappingComponent['constraints'],
): AdcmMappingComponent => ({
  ...component,
  constraints,
});
