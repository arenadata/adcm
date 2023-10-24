import { Button } from '@uikit';
import s from './ClusterImportToolbar.module.scss';

export interface ClusterImportToolbarProps extends React.PropsWithChildren {
  onClick: () => void;
  hasError: boolean;
  isDisabled: boolean;
}

const ClusterImportToolbar = ({ onClick, hasError, isDisabled, children }: ClusterImportToolbarProps) => {
  return (
    <div className={s.clusterImportToolbar}>
      <div>{children}</div>
      <Button disabled={isDisabled} onClick={onClick} hasError={hasError}>
        Import
      </Button>
    </div>
  );
};

export default ClusterImportToolbar;
