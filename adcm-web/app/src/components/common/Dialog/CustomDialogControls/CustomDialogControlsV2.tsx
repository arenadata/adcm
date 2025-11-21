import { type DialogDefaultControlsPropsV2, DialogDefaultControlsV2 } from '@uikit';
import s from './CustomDialogControls.module.scss';
import cn from 'classnames';

interface CustomDialogControlsProps extends DialogDefaultControlsPropsV2, React.PropsWithChildren {
  className?: string;
}

// It's a temporary component, while updating dialogs to DialogV2
const CustomDialogControls = ({ children, className, ...controlsProps }: CustomDialogControlsProps) => {
  return (
    <div className={cn(s.customDialogControls, className)}>
      {children}
      <DialogDefaultControlsV2 {...controlsProps} />
    </div>
  );
};

export default CustomDialogControls;
