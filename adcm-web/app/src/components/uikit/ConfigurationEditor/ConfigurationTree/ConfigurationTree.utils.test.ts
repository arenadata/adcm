/* eslint-disable @typescript-eslint/no-non-null-assertion */
/* eslint-disable @typescript-eslint/no-non-null-asserted-optional-chain */
import { schema, configuration } from './ConfigurationTree.utils.test.constants';
import { buildTreeNodes, filterTreeNodes } from './ConfigurationTree.utils';

describe('filter', () => {
  test('find something', () => {
    const tree = buildTreeNodes(schema, configuration, {});
    const filteredTree = filterTreeNodes(tree, { title: 'Name', showAdvanced: false, showInvisible: false });
    const rootNode = filteredTree;
    expect(rootNode).not.toBe(undefined);
    expect(rootNode.key).toBe('root-node');
    expect(rootNode.children?.length).toBe(1);

    const clusterConfigNode = filteredTree.children?.[0]!;
    expect(clusterConfigNode.key).toBe('/cluster_config');
    expect(clusterConfigNode.children?.length).toBe(1);

    const clusterNode = clusterConfigNode.children?.[0]!;
    expect(clusterNode.key).toBe('/cluster_config/cluster');
    expect(clusterNode.children?.length).toBe(1);

    const clusterNameNode = clusterNode.children?.[0]!;
    expect(clusterNameNode.key).toBe('/cluster_config/cluster/cluster_name');
    expect(clusterNameNode.children).toBe(undefined);
  });
});

describe('fillFieldAttributes', () => {
  test('Fill Field Attributes', () => {
    const clusterConfigAttributes = { isActive: true, isSynchronized: true };
    const clusterAttributes = { isActive: true, isSynchronized: false };
    const authAttributes = { isActive: false, isSynchronized: true };

    const attributes = {
      '/cluster_config': clusterConfigAttributes,
      '/cluster_config/cluster': clusterAttributes,
      '/cluster_config/auth': authAttributes,
    };

    const tree = buildTreeNodes(schema, configuration, attributes);

    const rootNode = tree;

    const clusterConfigNode = rootNode.children?.[0]!;
    expect(clusterConfigNode.data.fieldAttributes).toStrictEqual(clusterConfigAttributes);

    const clusterNode = clusterConfigNode.children?.[0]!;
    expect(clusterNode.data.fieldAttributes).toStrictEqual(clusterAttributes);

    const authNode = clusterConfigNode.children?.[1]!;
    expect(authNode.data.fieldAttributes).toStrictEqual(authAttributes);
  });
});
