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

/**
 * @deprecated
 */
export const swapTitleAsPropertyName = (schema: Schema): Schema => {
  if (typeof schema === 'boolean') {
    return schema;
  }

  const result = JSON.parse(JSON.stringify(schema));

  if (result.type === 'object') {
    const props = Object.keys(result.properties);

    const required = new Set(result.required ?? []);

    for (const propName of props) {
      const title = result.properties[propName].title;
      const newPropName = title ?? propName;
      result.properties[newPropName] = swapTitleAsPropertyName(result.properties[propName]);

      if (title && propName !== title) {
        result.properties[newPropName].title = propName;
        delete result.properties[propName];
      }

      if (title && required.has(propName) && propName !== title) {
        required.delete(propName);
        required.add(title);
      }
    }

    if (result.required) {
      result.required = [...required];
    }
  }

  if (result.type === 'array') {
    result.items = swapTitleAsPropertyName(result.items);
  }

  const compositionKey = result.oneOf ? 'oneOf' : result.anyOf ? 'anyOf' : result.allOf ? 'allOf' : undefined;
  if (compositionKey && result[compositionKey]) {
    for (let i = 0; i < result[compositionKey].length; i++) {
      result[compositionKey][i] = swapTitleAsPropertyName(result[compositionKey][i]);
    }
  }

  return result;
};

// const iterateObjectPropsAndSwap
