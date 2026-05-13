import type { SchemaDefinition } from '@models/adcm';
import type { JSONObject } from '@models/json';
import {
  buildOneOfMetaAttributesSyncPayload,
  collectMetaAttributesForSchema,
  syncFieldAttributes,
} from './ConfigurationTreeAttributes.utils';
import { discriminatorFieldName } from './ConfigurationTree.constants';

describe('ConfigurationTreeAttributes.utils', () => {
  test('syncFieldAttributes removes exact keys and applies addPaths', () => {
    const base = {
      '/a': { isActive: false, isSynchronized: true },
      '/b': { isActive: true },
      '/c': {},
    };

    const next = syncFieldAttributes(base, {
      removePaths: ['/b'],
      addPaths: [
        { path: '/a', fieldAttributes: { isActive: true } },
        { path: '/d', fieldAttributes: { isActive: false } },
      ],
    });

    expect(next).toEqual({
      '/a': { isActive: true },
      '/c': {},
      '/d': { isActive: false },
    });
  });

  test('collectMetaAttributesForSchema supports defaults and nested selectable groups', () => {
    const schema: SchemaDefinition = {
      type: 'object',
      properties: {
        outer: {
          type: 'object',
          oneOf: [
            {
              type: 'object',
              properties: {
                _selection: { const: 'a' } as unknown as SchemaDefinition,
                a: {
                  type: 'object',
                  properties: {
                    // nested selectable
                    inner: {
                      type: 'object',
                      oneOf: [
                        {
                          type: 'object',
                          properties: {
                            _selection: { const: 'x' } as unknown as SchemaDefinition,
                            x: {
                              type: 'object',
                              properties: {
                                act: {
                                  type: 'object',
                                  adcmMeta: { activation: { isAllowChange: true, default: false } },
                                  properties: {},
                                },
                                sync: {
                                  type: 'object',
                                  adcmMeta: { synchronization: { isAllowChange: true, default: true } },
                                  properties: {},
                                },
                              },
                            },
                          },
                        },
                      ],
                      discriminator: { propertyName: discriminatorFieldName },
                    },
                  },
                },
              },
            },
          ],
          discriminator: { propertyName: discriminatorFieldName },
        },
      },
    };

    const value: JSONObject = {
      outer: {
        [discriminatorFieldName]: 'a',
        a: {
          inner: {
            [discriminatorFieldName]: 'x',
            x: {},
          },
        },
      },
    };

    const out = new Map<string, { isActive?: boolean; isSynchronized?: boolean }>();
    collectMetaAttributesForSchema(schema, [], value, out);

    expect(out.get('/outer/a/inner/x/act')).toEqual({ isActive: false });
    expect(out.get('/outer/a/inner/x/sync')).toEqual({ isSynchronized: true });
  });

  test('buildOneOfMetaAttributesSyncPayload removes old branch meta and adds new branch meta', () => {
    const fieldSchema: SchemaDefinition = {
      type: 'object',
      oneOf: [
        {
          type: 'object',
          properties: {
            _selection: { const: 'group1' } as unknown as SchemaDefinition,
            group1: {
              type: 'object',
              properties: {
                activatable_group: {
                  type: 'object',
                  adcmMeta: { activation: { isAllowChange: true } },
                  properties: {},
                },
              },
            },
          },
        },
        {
          type: 'object',
          properties: {
            _selection: { const: 'group2' } as unknown as SchemaDefinition,
            group2: {
              type: 'object',
              properties: {},
            },
          },
        },
      ],
      discriminator: { propertyName: discriminatorFieldName },
    };

    const currentValue: JSONObject = { [discriminatorFieldName]: 'group1', group1: {} };
    const nextValue: JSONObject = { [discriminatorFieldName]: 'group2', group2: {} };

    const payload = buildOneOfMetaAttributesSyncPayload(fieldSchema, currentValue, nextValue, ['selection_group']);

    expect(payload.removePaths).toEqual(['/selection_group/group1/activatable_group']);
    expect(payload.addPaths).toEqual([]);
  });
});
