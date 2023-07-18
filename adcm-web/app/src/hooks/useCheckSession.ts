import { useEffect } from 'react';
import { useDispatch } from './useDispatch';
import { checkSession } from '@store/userSlice';
import { useStore } from '@hooks';

export const useCheckSession = () => {
  const dispatch = useDispatch();
  const { needCheckSession } = useStore((s) => s.user);

  useEffect(() => {
    needCheckSession && dispatch(checkSession());
  }, [dispatch, needCheckSession]);
};
