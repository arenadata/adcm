/* eslint-disable spellcheck/spell-checker */
import { safePattern } from './patternKeyword';
import Ajv2020, { Schema } from 'ajv/dist/2020';

const ajv = new Ajv2020({
  strictSchema: true,
  allErrors: true,
  verbose: true,
  unicodeRegExp: false,
});

ajv.addVocabulary(['adcmMeta']);
ajv.removeKeyword('pattern');
ajv.addKeyword(safePattern);

const ajvWithDefaults = new Ajv2020({
  strictSchema: false,
  useDefaults: true,
  allErrors: true,
});

ajvWithDefaults.addVocabulary(['adcmMeta']);
ajvWithDefaults.addFormat('json', true);
ajvWithDefaults.addFormat('yaml', true);

export const validate = <T>(schema: Schema, data: T) => {
  const validate = ajv.compile<T>(schema, true);
  validate(data);

  return validate.errors;
};

export const generateFromSchema = <T>(schema: Schema): T | null => {
  if (typeof schema === 'object') {
    if (schema.oneOf !== undefined) {
      return null;
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

export { Schema };

export const getPatternErrorMessage = (pattern: string) => `The value must match pattern: ${pattern}`;
