import { type DialogDefaultControlsPropsV2, DialogDefaultControlsV2 } from '@uikit';
import s from './CustomDialogControls.module.scss';

interface CustomDialogControlsProps extends DialogDefaultControlsPropsV2, React.PropsWithChildren {}

// It's a temporary component, while updating dialogs to DialogV2
const CustomDialogControls = ({ children, ...controlsProps }: CustomDialogControlsProps) => {
  return (
    <div className={s.customDialogControls}>
      {children}
      <DialogDefaultControlsV2 {...controlsProps} />
    </div>
  );
};

export default CustomDialogControls;
