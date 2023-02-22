import { HttpErrorResponse } from '@angular/common/http';
import { DjangoHttpError } from './django-http-error';

export class DjangoHttpErrorResponse extends HttpErrorResponse {

  error: DjangoHttpError;

}
