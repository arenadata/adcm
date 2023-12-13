import isSafari from '@braintree/browser-detection/dist/is-safari';

(() => {
  if (isSafari(navigator.userAgent)) {
    document.body.classList.add('is-ugly-safari');
  }
})();
