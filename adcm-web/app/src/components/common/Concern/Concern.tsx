import React from 'react';
import ConcernMessages from './ConcernMessages/ConcernMessages';
import Tooltip from '@uikit/Tooltip/Tooltip';
import Icon from '@uikit/Icon/Icon';
import s from './Concern.module.scss';
import { AdcmConcerns } from '@models/adcm';
import { getConcernLinkObjectPathsDataArray } from '@utils/concernUtils';
import cn from 'classnames';

interface ConcernProps {
  concerns: AdcmConcerns[];
  className?: string;
}

const Concern: React.FC<ConcernProps> = ({ concerns, className }) => {
  if (concerns.length === 0) {
    return null;
  }

  const hasError = concerns.some(({ isBlocking }) => isBlocking);
  const classes = cn(className, {
    [s.concern_error]: hasError,
    [s.concern_warning]: !hasError && concerns.length > 0,
  });

  const concernsDataArray = getConcernLinkObjectPathsDataArray(concerns);

  return (
    <>
      <Tooltip label={<ConcernMessages concernsData={concernsDataArray} />} placement={'bottom-start'} closeDelay={100}>
        <Icon name="g1-info" size={32} className={classes} />
      </Tooltip>
    </>
  );
};

export default Concern;
