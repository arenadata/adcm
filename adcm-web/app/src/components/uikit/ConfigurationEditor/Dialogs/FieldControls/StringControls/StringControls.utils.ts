import type { SchemaDefinition } from '@models/adcm';
import { getPatternErrorMessage } from '@utils/jsonSchema/jsonSchemaUtils';

export const validate = (value: string, fieldSchema: SchemaDefinition): string | undefined => {
  if (fieldSchema.pattern) {
    try {
      const re = new RegExp(fieldSchema.pattern);
      if (!re.test(value)) {
        return getPatternErrorMessage(fieldSchema.pattern);
      }
    } catch (_e) {
      return 'invalid pattern';
    }
  }

  if (fieldSchema.format === 'json') {
    try {
      if (value && value.trim() !== '') {
        const parsed = JSON.parse(value);
        if (typeof parsed !== 'object' || parsed === null) {
          return 'JSON must be an Object or Array';
        }
      }
    } catch (e) {
      return (e as Error).message || 'Invalid JSON syntax';
    }
  }

  return undefined;
};
