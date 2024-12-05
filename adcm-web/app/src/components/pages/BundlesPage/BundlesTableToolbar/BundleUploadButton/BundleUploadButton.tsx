import type { ChangeEvent } from 'react';
import type React from 'react';
import { useRef } from 'react';
import { Button } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { uploadWithUpdateBundles } from '@store/adcm/bundles/bundlesActionsSlice';

const BundleUploadButton: React.FC = () => {
  const dispatch = useDispatch();
  const isUploading = useStore(({ adcm }) => adcm.bundlesActions.isUploading);

  const inputRef = useRef<HTMLInputElement | null>(null);

  const clearFile = () => {
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { files } = e.target;
    if (files === null || isUploading) return;

    dispatch(uploadWithUpdateBundles([...files])).then(() => {
      // we shouldn't use .unwrap() for dispatch, because we should clear file for success and failed done
      clearFile();
    });
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  return (
    <>
      <Button
        onClick={handleClick}
        disabled={isUploading}
        iconLeft={isUploading ? { name: 'g1-load', className: 'spin' } : 'g1-imports'}
      >
        Upload bundle
      </Button>
      <input
        ref={inputRef}
        onChange={handleFileChange}
        type="file"
        multiple
        accept=".tar, .tar.gz, .tgz"
        className="hidden"
      />
    </>
  );
};

export default BundleUploadButton;
