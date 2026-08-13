import type { SchemaDefinition } from '@models/adcm';

export type InlinePrimitiveFieldControlType = 'string' | 'number' | 'boolean' | 'enum';

export const getInlinePrimitiveFieldControlType = (
  fieldSchema: SchemaDefinition,
): InlinePrimitiveFieldControlType | null => {
  if (fieldSchema.enum) {
    return 'enum';
  }

  switch (fieldSchema.type) {
    case 'string': {
      const isMultiline = fieldSchema.adcmMeta?.stringExtra?.isMultiline;
      const isSecret = fieldSchema.adcmMeta?.isSecret;

      if (isMultiline || isSecret) {
        return null;
      }

      return 'string';
    }
    case 'integer':
    case 'number': {
      return 'number';
    }
    case 'boolean': {
      return 'boolean';
    }
    default: {
      return null;
    }
  }
};

export const isInlineEditablePrimitiveField = (fieldSchema: SchemaDefinition): boolean =>
  getInlinePrimitiveFieldControlType(fieldSchema) !== null;
