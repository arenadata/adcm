import React from 'react';

interface ConcernMessagesProps {
  messages: string[];
}

const ConcernMessages: React.FC<ConcernMessagesProps> = ({ messages }) => {
  return (
    <>
      {messages.map((message, index) => (
        <div key={index}>{message}</div>
      ))}
    </>
  );
};

export default ConcernMessages;
