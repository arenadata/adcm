import type React from 'react';
import { AdcmFieldAttributesCtx } from './AdcmFieldAttributes.context';
import type { FieldAttributes } from '@models/adcm';
import type { ChangeFieldAttributesHandler } from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.types';

export interface AdcmFieldAttributesWidgetProps extends React.PropsWithChildren {
  path: string;
  attributes: FieldAttributes;
  onFieldAttributesChange: ChangeFieldAttributesHandler;
  onCancel: () => void;
}

const AdcmFieldAttributesWidgetProvider = ({ children, ...value }: AdcmFieldAttributesWidgetProps) => {
  return <AdcmFieldAttributesCtx.Provider value={value}>{children}</AdcmFieldAttributesCtx.Provider>;
};

export default AdcmFieldAttributesWidgetProvider;
