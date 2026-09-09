import { safePattern } from './patternKeyword';
import Ajv2020, { type Schema } from 'ajv/dist/2020';

const ajv = new Ajv2020({
  strictSchema: true,
  allErrors: true,
  verbose: true,
  unicodeRegExp: false,
  discriminator: true,
});

ajv.addVocabulary(['adcmMeta']);
ajv.removeKeyword('pattern');
ajv.addKeyword(safePattern);

const ajvWithDefaults = new Ajv2020({
  strictSchema: false,
  useDefaults: true,
  allErrors: true,
  discriminator: true,
});

ajvWithDefaults.addVocabulary(['adcmMeta']);
ajvWithDefaults.addFormat('json', true);
ajvWithDefaults.addFormat('yaml', true);

export const validate = <T>(schema: Schema, data: T) => {
  const validate = ajv.compile<T>(schema, true);
  validate(data);

  return validate.errors;
};

export type SchemaLike = Schema | object | boolean;

export const validateSchemaLikeWithAjv = (schema: SchemaLike, data: unknown) => {
  // `true` / `false` are valid JSON Schemas (boolean schemas).
  if (schema === true) return null;

  try {
    return validate(schema as Schema, data);
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    // Return a synthetic root error so callers can render and surface the failure without crashing.
    return [
      {
        instancePath: '/',
        parentSchema: schema as Schema,
        data,
        keyword: '$ref',
        message,
        params: {},
      },
    ];
  }
};

export const generateFromSchema = <T>(schema: Schema): T | null => {
  if (typeof schema === 'object') {
    if (schema.oneOf !== undefined) {
      const tmpSchema: Schema = {
        type: 'object',
        properties: {
          t: { ...schema },
        },
      };

      // t property required for applying defaults (defaults applies only for object properties and not for object itself)
      const result = { t: undefined } as { t: T };
      const validate = ajvWithDefaults.compile(tmpSchema);
      validate(result);

      return result.t;
    }

    if (schema.type === 'object') {
      const result = {} as T;
      const validate = ajvWithDefaults.compile(schema);
      validate(result);

      return result;
    }

    return schema.default;
  }

  return null;
};

export type { Schema };

export const getPatternErrorMessage = (pattern: string) => `The value must match pattern: ${pattern}`;
