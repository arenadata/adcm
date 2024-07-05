import ErrorPageContent from '@commonComponents/ErrorPageContent/ErrorPageContent';
import ErrorTextContainer from '@commonComponents/ErrorPageContent/ErrorTextContainer/ErrorTextContainer';

const AccessDeniedPage = () => {
  return (
    <>
      <ErrorPageContent errorCode="403">
        <ErrorTextContainer errorHeader="Access denied">
          <div>You lack permissions to access this page.</div>
          <div>Please contact your system administrator for more information.</div>
        </ErrorTextContainer>
      </ErrorPageContent>
    </>
  );
};

export default AccessDeniedPage;
