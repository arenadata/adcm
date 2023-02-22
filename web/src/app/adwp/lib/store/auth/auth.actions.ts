import { createAction, props } from '@ngrx/store';

export const authCheck = createAction('[Auth] Check');
export const authLogin = createAction('[Auth] Login', props<{ username: string; password: string }>());
export const authSuccess = createAction('[Auth] LoginSuccess', props<{ username: string }>());
export const authFailed = createAction('[Auth] LoginFailed', props<{ message: string }>());
export const authLogout = createAction('[Auth] Logout');
