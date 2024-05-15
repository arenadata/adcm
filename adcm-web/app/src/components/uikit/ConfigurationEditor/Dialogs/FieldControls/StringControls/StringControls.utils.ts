import { SingleSchemaDefinition } from '@models/adcm';
import { getPatternErrorMessage } from '@utils/jsonSchemaUtils';

export const validate = (value: string, fieldSchema: SingleSchemaDefinition): string | undefined => {
  let error = undefined;
  if (fieldSchema.pattern) {
    const re = new RegExp(fieldSchema.pattern);
    if (!re.test(value)) {
      error = getPatternErrorMessage(fieldSchema.pattern);
    }
  }

  return error;
};
