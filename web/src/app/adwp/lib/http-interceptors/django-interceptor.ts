import { Injectable } from '@angular/core';
import { HttpInterceptor } from '@angular/common/http';
import { HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Cookie } from '../helpers/cookie';
import { AuthService } from '../services/auth.service';

@Injectable()
export class DjangoInterceptor implements HttpInterceptor {

  readonly HEADER_NAME = 'X-CSRFToken';

  constructor(
    private authService: AuthService,
  ) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const tokenCookieName = this.authService.getTokenCookieName();
    if (tokenCookieName) {
      const token = Cookie.get(tokenCookieName);
      if (token !== undefined && !req.headers.has(this.HEADER_NAME) && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(req.method)) {
        req = req.clone({ headers: req.headers.set(this.HEADER_NAME, token) });
      }
    }
    return next.handle(req);
  }

}
