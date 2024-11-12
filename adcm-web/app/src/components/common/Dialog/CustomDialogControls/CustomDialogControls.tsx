import type { DialogDefaultControlsProps } from '@uikit';
import { DialogDefaultControls } from '@uikit';
import s from './CustomDialogControls.module.scss';

interface CustomDialogControlsProps extends DialogDefaultControlsProps, React.PropsWithChildren {}

const CustomDialogControls = ({ children, ...controlsProps }: CustomDialogControlsProps) => {
  return (
    <div className={s.customDialogControls}>
      {children}
      <DialogDefaultControls {...controlsProps} />
    </div>
  );
};

export default CustomDialogControls;
