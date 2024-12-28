import type { SingleSchemaDefinition } from '@models/adcm';
import { getPatternErrorMessage } from '@utils/jsonSchema/jsonSchemaUtils';

export const validate = (value: string, fieldSchema: SingleSchemaDefinition): string | undefined => {
  let error = undefined;
  if (fieldSchema.pattern) {
    try {
      const re = new RegExp(fieldSchema.pattern);
      if (!re.test(value)) {
        error = getPatternErrorMessage(fieldSchema.pattern);
      }
    } catch (_e) {
      return 'invalid pattern';
    }
  }

  return error;
};
