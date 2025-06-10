import type React from 'react';
import type { ConcernObjectPathsData } from '@utils/concernUtils';
import { Link } from 'react-router-dom';
import s from './ConcernMeassages.module.scss';
import IconButton from '@uikit/IconButton/IconButton';
import { deleteClusterConcern } from '@store/adcm/concerns/concernsActionSlice';
import { useDispatch } from '@hooks';

interface ConcernMessagesProps {
  concernsData: {
    concernId: number;
    isDeletable: boolean;
    concernData: ConcernObjectPathsData[];
  }[];
}

const ConcernMessages: React.FC<ConcernMessagesProps> = ({ concernsData }) => {
  const dispatch = useDispatch();

  const handleDeleteConcern = (concernId: number) => {
    dispatch(deleteClusterConcern(concernId));
  };

  return (
    <>
      {concernsData.map((concernData) => (
        <div key={concernData.concernId} className={s.concernMessage}>
          {concernData.concernData.map((messagePart, messageIndex) =>
            messagePart.path ? (
              // biome-ignore lint/suspicious/noArrayIndexKey:
              <Link key={messageIndex} to={messagePart.path} className="text-link">
                {messagePart.text}
              </Link>
            ) : (
              messagePart.text
            ),
          )}
          {concernData.isDeletable && (
            <IconButton
              className={s.concernMessage__removeButton}
              icon="g2-close"
              size={18}
              variant="secondary"
              onClick={() => handleDeleteConcern(concernData.concernId)}
            />
          )}
        </div>
      ))}
    </>
  );
};

export default ConcernMessages;
