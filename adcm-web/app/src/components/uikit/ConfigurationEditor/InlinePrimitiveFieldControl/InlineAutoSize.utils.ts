import type { CSSProperties } from 'react';
import type { JSONPrimitive } from '@models/json';
import { isPrimitiveValueSet } from '@models/json';
import { isWhiteSpaceOnly } from '@utils/validationsUtils';
import { emptyStringStub, nullStub, whiteSpaceStringStub } from '../ConfigurationTree/ConfigurationTree.constants';

export const MIN_NUMBER_INPUT_WIDTH_CH = 6;
export const NUMBER_INPUT_BUFFER_CH = 2;
export const INLINE_ENUM_PLACEHOLDER = 'Select';

export const getInlineStringDisplayText = (value: JSONPrimitive): string => {
  if (!isPrimitiveValueSet(value)) {
    return nullStub;
  }

  if (value === '') {
    return emptyStringStub;
  }

  if (isWhiteSpaceOnly(value.toString())) {
    return whiteSpaceStringStub;
  }

  return value.toString();
};

export const isInlineStringDisplayStub = (value: JSONPrimitive): boolean => {
  if (!isPrimitiveValueSet(value)) {
    return true;
  }

  if (value === '') {
    return true;
  }

  return isWhiteSpaceOnly(value.toString());
};

export const getInlineStringEditValue = (value: JSONPrimitive): string => {
  if (!isPrimitiveValueSet(value)) {
    return '';
  }

  return value.toString();
};

export const getNumberInputWidthCh = (value: string): number => {
  const digitCount = value.length || 1;

  return Math.max(MIN_NUMBER_INPUT_WIDTH_CH, digitCount + NUMBER_INPUT_BUFFER_CH);
};

export const getNumberInputWidthStyle = (value: string): CSSProperties =>
  ({
    '--inline-number-input-width': `${getNumberInputWidthCh(value)}ch`,
  }) as CSSProperties;

interface GetInlineValueStyleOptions {
  isInlineNumberField: boolean;
  value: unknown;
}

export const getInlineValueStyle = ({
  isInlineNumberField,
  value,
}: GetInlineValueStyleOptions): CSSProperties | undefined => {
  if (isInlineNumberField) {
    const numberValue = !isPrimitiveValueSet(value as JSONPrimitive) ? nullStub : String(value);

    return getNumberInputWidthStyle(numberValue);
  }

  return undefined;
};
