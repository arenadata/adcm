import { Button } from '@uikit';
import s from './ClusterImportToolbar.module.scss';

export interface ClusterImportToolbarProps extends React.PropsWithChildren {
  onClick: () => void;
  hasError: boolean;
  isDisabled: boolean;
  isImportPresent: boolean;
}

const ClusterImportToolbar = ({
  onClick,
  hasError,
  isDisabled,
  children,
  isImportPresent,
}: ClusterImportToolbarProps) => {
  return (
    <div className={s.clusterImportToolbar}>
      <div>{children}</div>
      <Button disabled={isDisabled} onClick={onClick} hasError={hasError}>
        {isImportPresent ? 'Save' : 'Import'}
      </Button>
    </div>
  );
};

export default ClusterImportToolbar;
