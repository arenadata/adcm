import React from 'react';
import { ConcernObjectPathsData } from '@utils/concernUtils';
import { Link } from 'react-router-dom';
import s from './ConcernMeassages.module.scss';

interface ConcernMessagesProps {
  concernsData: Array<ConcernObjectPathsData[]>;
}

const ConcernMessages: React.FC<ConcernMessagesProps> = ({ concernsData }) => {
  return (
    <>
      {concernsData.map((concernData, index) => (
        <div key={index} className={s.concernMessage}>
          {concernData.map((messagePart, messageIndex) =>
            messagePart.path ? (
              <Link key={messageIndex} to={messagePart.path} className="text-link">
                {messagePart.text}
              </Link>
            ) : (
              messagePart.text
            ),
          )}
        </div>
      ))}
    </>
  );
};

export default ConcernMessages;
