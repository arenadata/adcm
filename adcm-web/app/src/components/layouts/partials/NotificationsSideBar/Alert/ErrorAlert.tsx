import React, { useMemo } from 'react';
import type { ErrorNotification } from '@models/notification';
import Alert from './Alert';
import type { AlertOptions } from './Alert.types';

import s from './Alert.module.scss';
import type { HTMLReactParserOptions } from 'html-react-parser';
import parse, { Element } from 'html-react-parser';

const ErrorAlert: React.FC<ErrorNotification & AlertOptions> = ({ model: { message }, onClose }) => {
  const parsedMessage = useMemo(() => {
    if (!message) return null;

    const parseOptions: HTMLReactParserOptions = {
      replace: (domNode) => {
        if (domNode instanceof Element && domNode.attribs && domNode.name === 'a') {
          domNode.attribs.class = [domNode.attribs.class, 'text-link'].join(' ');
        }
        return domNode;
      },
    };

    return parse(message, parseOptions);
  }, [message]);

  return (
    <Alert icon="triangle-alert" className={s.alert_error} onClose={onClose}>
      {parsedMessage}
    </Alert>
  );
};

export default ErrorAlert;
