import { SingleSchemaDefinition } from '@models/adcm';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';

export const getEnumOptions = (fieldSchema: SingleSchemaDefinition) => {
  if (fieldSchema.enum === undefined) {
    return [];
  }

  const labels: string[] = fieldSchema.adcmMeta.enumExtra?.labels ?? [];
  const enumValues = fieldSchema.enum as unknown[];

  const options =
    labels.length === fieldSchema.enum.length
      ? getOptionsFromArray(
          enumValues,
          (v, i) => labels[i],
          (v) => v,
        )
      : getOptionsFromArray(
          enumValues,
          (v) => v?.toString() ?? '',
          (v) => v,
        );

  return options;
};
