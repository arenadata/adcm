/* eslint-disable spellcheck/spell-checker */
import Ajv2020, { Schema, ErrorObject } from 'ajv/dist/2020';

const ajv = new Ajv2020({
  strictSchema: true,
  allErrors: true,
});

ajv.addVocabulary(['adcmMeta']);

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
  const isValid = validate(data);

  return {
    isValid,
    errors: validate.errors,
    errorsPaths: getAllErrorInstancePaths(validate.errors),
    evaluated: validate.evaluated,
    schema: validate.schema,
    schemaEnv: validate.schemaEnv,
    source: validate.source,
  };
};

const getAllErrorInstancePaths = (errors: ErrorObject[] | undefined | null) => {
  const result: Record<string, string | true> = {}; // key - path, value - message or true (true means that child node has error)
  if (!errors) {
    return result;
  }

  for (const error of errors) {
    let instancePath = error.instancePath;
    let errorMessage = error.message;

    // extend error from structure to field
    if (error.keyword === 'required') {
      instancePath += `/${error.params.missingProperty}`;
      errorMessage = 'required';
    }

    const parts = instancePath.split('/');
    let path = '';
    for (const part of parts) {
      if (part) {
        path = `${path}/${part}`;
        result[path] = true;
      }
    }
    result[instancePath] = errorMessage ?? '';
  }

  return result;
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
