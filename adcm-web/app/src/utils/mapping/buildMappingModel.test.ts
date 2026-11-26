import { buildMappingModel } from './buildMappingModel';
import { hosts, components, pairsAlphaZkServer } from './__fixtures__/mappingFixtures';

describe('buildMappingModel', () => {
  test('buildMappingModel projections match pairs', () => {
    const model = buildMappingModel(pairsAlphaZkServer, hosts, components);
    const zk = model.componentsMapping.find((c) => c.component.name === 'zk_server');
    expect(zk?.hosts.map((h) => h.name)).toEqual(['alpha']);
    expect(model.servicesMapping.map((s) => s.service.name).sort()).toEqual(['hbase', 'zookeeper']);
    expect(model.hostsMapping).toHaveLength(hosts.length);
  });
});
