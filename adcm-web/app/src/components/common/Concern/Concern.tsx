import React from 'react';
import ConcernInfo from './ConcernMessages/ConcernMessages';
import Tooltip from '@uikit/Tooltip/Tooltip';
import Icon from '@uikit/Icon/Icon';
import s from './Concern.module.scss';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import { AdcmConcerns } from '@models/adcm';
import { formatConcernMessage } from '@utils/concernUtils';
import cn from 'classnames';

interface ConcernProps {
  concerns: AdcmConcerns[];
  className?: string;
}

const Concern: React.FC<ConcernProps> = ({ concerns, className }) => {
  const hasError = concerns.some(({ isBlocking }) => isBlocking);
  const classes = cn(className, {
    [s.concern_error]: hasError,
    [s.concern_warning]: !hasError && concerns.length > 0,
  });

  const concernMessages: string[] = concerns.map((concern) => formatConcernMessage(concern.reason));

  return (
    <>
      <ConditionalWrapper
        Component={Tooltip}
        isWrap={concernMessages.length > 0}
        label={<ConcernInfo messages={concernMessages} />}
        placement={'bottom-start'}
      >
        <Icon name="g1-info" size={32} className={classes} />
      </ConditionalWrapper>
    </>
  );
};

export default Concern;
