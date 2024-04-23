import { isClusterNameValid } from './validationsUtils';

test('cluster name test', () => {
  const nameTest = isClusterNameValid('Cluster_1 - new');

  expect(nameTest).toBeTruthy();
});
