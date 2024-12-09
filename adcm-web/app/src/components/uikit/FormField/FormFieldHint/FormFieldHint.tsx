import type React from 'react';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import s from '../FormField.module.scss';
import Tooltip from '@uikit/Tooltip/Tooltip';
import cn from 'classnames';

interface FormFieldHintProps {
  description?: React.ReactNode;
  hasError?: boolean;
}
const FormFieldHint: React.FC<FormFieldHintProps> = ({ description, hasError }) => {
  return (
    <>
      {hasError && <MarkerIcon type="alert" variant="square" className={s.formField__marker} />}
      {description && (
        <Tooltip label={description} placement="top-start">
          <MarkerIcon type="info" variant="square" className={cn(s.formField__marker, s.formField__marker_info)} />
        </Tooltip>
      )}
    </>
  );
};

export default FormFieldHint;
