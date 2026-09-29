import { sanitizeAllowedHtml } from '../sanitizeUtils';

describe('sanitizeAllowedHtml', () => {
  it('should strip unknown tags and keep their text when preserveUnknownTagsAsText is false', () => {
    const result = sanitizeAllowedHtml('<h1>Title</h1><p>body</p>', {
      preserveUnknownTagsAsText: false,
    });

    expect(result).toBe('Title<p>body</p>');
    expect(result).not.toContain('&lt;h1&gt;');
  });

  it('should escape unknown tags as text when preserveUnknownTagsAsText is true', () => {
    const result = sanitizeAllowedHtml('Errors: <Host #38 host3>. <p>ok</p>', {
      preserveUnknownTagsAsText: true,
    });

    expect(result).toContain('&lt;Host #38 host3&gt;');
    expect(result).toContain('<p>ok</p>');
  });

  it('should default to stripping unknown tags (MainInfo-safe path)', () => {
    const result = sanitizeAllowedHtml('<code>x</code> and <p>y</p>');

    expect(result).toBe('x and <p>y</p>');
  });

  it('should strip event handlers from allowed tags', () => {
    const result = sanitizeAllowedHtml('<span onclick="alert(1)">click</span>');

    expect(result).toBe('<span>click</span>');
  });

  it('should remove javascript: and data: href values', () => {
    expect(sanitizeAllowedHtml('<a href="javascript:alert(1)">a</a>')).not.toMatch(/javascript:/i);
    expect(sanitizeAllowedHtml('<a href="data:text/html,x">a</a>')).not.toMatch(/data:/i);
  });

  it('should add noopener noreferrer when target is _blank', () => {
    const result = sanitizeAllowedHtml('<a href="/path" target="_blank">link</a>');

    expect(result).toContain('target="_blank"');
    expect(result).toMatch(/rel="[^"]*noopener/);
    expect(result).toMatch(/rel="[^"]*noreferrer/);
  });

  it('should keep safe relative links', () => {
    const result = sanitizeAllowedHtml('<a href="/adcm-web/app/public">Link</a>');

    expect(result).toBe('<a href="/adcm-web/app/public">Link</a>');
  });
});
