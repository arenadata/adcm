import { getCompareView } from './CompareConfiguration.utils';
import { fieldSchema, listSchema, structureSchema } from './CompareConfiguration.utils.test.constants';

test('field', () => {
  const config = {
    someField: 'value1',
  };

  const compareView = getCompareView(fieldSchema, config, {});
  const expectedView = {
    'Some field': 'value1',
  };

  expect(compareView).toStrictEqual(expectedView);
});

test('array', () => {
  const config = {
    list: ['value1', 'value2'],
  };

  const compareView = getCompareView(listSchema, config, {});
  const expectedView = {
    'Some array': ['value1', 'value2'],
  };

  expect(compareView).toStrictEqual(expectedView);
});

test('structure', () => {
  const config = {
    structure: {
      someField1: 'value1',
      someField2: 'value2',
    },
  };

  const compareView = getCompareView(structureSchema, config, {});
  const expectedView = {
    'Some structure': {
      'Some field1': 'value1',
      'Some field2': 'value2',
    },
  };

  expect(compareView).toStrictEqual(expectedView);
});
