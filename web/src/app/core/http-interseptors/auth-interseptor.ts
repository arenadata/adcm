// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { HttpErrorResponse, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { Location } from '@angular/common';
import { Observable, throwError } from 'rxjs';
import { catchError, finalize } from 'rxjs/operators';

import { AuthService } from '@app/core/auth/auth.service';
import { ChannelService, keyChannelStrim, PreloaderService, ResponseError, ResponseErrorCode } from '../services';

const EXCLUDE_URLS = ['/api/v1/rbac/token/', '/assets/config.json'];

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(
    private authService: AuthService,
    private preloader: PreloaderService,
    private router: Router,
    private channel: ChannelService,
    private location: Location
  ) {}

  addAuthHeader(request: HttpRequest<any>): HttpRequest<any> {
    const token = this.authService.token;
    if (token && !EXCLUDE_URLS.includes(request.url)) {
      const setParams = request.url.split('?').find((a, i) => i === 1 && a.includes('noview')) ? {} : { view: 'interface' };
      request = request.clone({ setHeaders: { Authorization: `Token ${token}` }, setParams });
    }

    return request;
  }

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<any> {
    this.preloader.start();
    request = this.addAuthHeader(request);
    return next.handle(request).pipe(
      catchError((res: HttpErrorResponse) => {
        this.authService.redirectUrl = this.router.url;

        if (res.status === 401) {
          this.router.navigate(['/login']);
        }

        if (res.status === 403) {
          let cur_path = this.location.path();
          this.location.back();
          if (cur_path === this.location.path()) {
            this.router.navigate(['/']);
          }
        }

        if (res.status === 500) this.router.navigate(['/500']);

        /** no need to show notification because error handling on landing page */
        const exclude = [ResponseErrorCode.UserNotFound, ResponseErrorCode.AuthError, ResponseErrorCode.ConfigNotFound];

        if (!exclude.includes(res.error.code)) {
          this.channel.next<ResponseError>(keyChannelStrim.error, res);
        }

        return throwError(res);
      }),
      finalize(() => this.preloader.end())
    );
  }
}
