import type { SingleSchemaDefinition } from '@models/adcm';
import { nullStub } from '../../ConfigurationTree/ConfigurationTree.constants';

export const getEnumOptions = (fieldSchema: SingleSchemaDefinition) => {
  if (fieldSchema.enum === undefined) {
    return [];
  }

  const labels: string[] = fieldSchema.adcmMeta.enumExtra?.labels ?? [];
  const enumValues = fieldSchema.enum as unknown[];

  const options =
    labels.length === fieldSchema.enum.length
      ? enumValues.map((v, i) => ({
          label: labels[i],
          value: v,
        }))
      : enumValues.map((v) => ({
          label: v?.toString() ?? nullStub,
          value: v,
        }));

  return options;
};
