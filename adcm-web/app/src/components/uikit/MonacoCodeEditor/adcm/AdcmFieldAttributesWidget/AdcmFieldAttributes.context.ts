import { createContext, useContext } from 'react';
import type { FieldAttributes } from '@models/adcm';
import type { ChangeFieldAttributesHandler } from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.types';

type AdcmFieldAttributesContextProps = {
  path: string;
  attributes: FieldAttributes;
  onFieldAttributesChange: ChangeFieldAttributesHandler;
  onCancel: () => void;
};

export const AdcmFieldAttributesCtx = createContext<AdcmFieldAttributesContextProps | null>(null);

export const useAdcmFieldAttributesContext = () => {
  const ctx = useContext(AdcmFieldAttributesCtx);
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
