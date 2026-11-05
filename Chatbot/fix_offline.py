#!/usr/bin/env python3
"""
Batch-fix broken external references in HTTrack mirror of www.sparrowi.com
for offline viewing.
"""

import os
import re
import glob

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, "www.sparrowi.com")


def get_all_html_files():
    """Get all HTML files under www.sparrowi.com."""
    files = []
    for root, dirs, fnames in os.walk(SITE):
        for f in fnames:
            if f.endswith(".html"):
                files.append(os.path.join(root, f))
    return files


def compute_relative_prefix(html_file):
    """Compute relative path prefix from html_file to www.sparrowi.com root."""
    rel = os.path.relpath(SITE, os.path.dirname(html_file))
    return rel.replace("\\", "/")


def fix_google_fonts(content, rel_prefix):
    """
    Replace Google Fonts <link> tags with a single local fonts-local.css link.
    Remove dns-prefetch for fonts.googleapis.com and preconnect for fonts.gstatic.com.
    """
    # Track if we've already inserted fonts-local.css
    fonts_local_inserted = False
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        # Remove dns-prefetch for fonts.googleapis.com
        if "dns-prefetch" in line and "fonts.googleapis.com" in line:
            continue

        # Remove preconnect for fonts.gstatic.com
        # This line often has other content after the preconnect tag
        if 'preconnect' in line and 'fonts.gstatic.com' in line:
            # The preconnect tag may be on same line as other content
            # e.g.: <link rel="preconnect" href="https://fonts.gstatic.com/" crossorigin><script ...>
            cleaned = re.sub(
                r'<link\s+rel=["\']preconnect["\']\s+href=["\']https?://fonts\.gstatic\.com/?["\']\s*(?:crossorigin)?/?>',
                '', line
            )
            if cleaned.strip():
                new_lines.append(cleaned)
            continue

        # Replace Google Fonts <link> tags
        if re.search(r'href=["\']https?://fonts\.googleapis\.com/css', line):
            if not fonts_local_inserted:
                new_lines.append(f"<link rel='stylesheet' href='{rel_prefix}/fonts-local.css' type='text/css' media='all' />")
                fonts_local_inserted = True
            # Skip the original Google Fonts link
            continue

        new_lines.append(line)

    return "\n".join(new_lines)


def fix_google_fonts_import(content):
    """Remove @import for Google Fonts (e.g., Unbounded) inside <style> blocks."""
    content = re.sub(
        r"@import\s+url\(['\"]https?://fonts\.googleapis\.com/[^)]+\)\s*;?",
        "/* Google Fonts @import removed for offline use */",
        content
    )
    return content


def remove_analytics(content):
    """Remove GTM, Google Analytics, Hotjar, and Google Ads tracking scripts."""

    # Remove dns-prefetch for googletagmanager.com
    content = re.sub(
        r"<link\s+rel='dns-prefetch'\s+href='https?://www\.googletagmanager\.com/?'\s*/?\s*>\s*\n?",
        "", content
    )

    # Remove Google Analytics/GTM <script src="...googletagmanager.com/gtag/js..."> tag
    content = re.sub(
        r'<!-- Google Analytics snippet added by Site Kit -->\s*\n?'
        r'<script[^>]*src=["\']https?://www\.googletagmanager\.com/gtag/js[^"\']*["\'][^>]*>\s*</script>\s*\n?'
        r'<script[^>]*id=["\']google_gtagjs-js-after["\'][^>]*>\s*\n?'
        r'/\*\s*<!\[CDATA\[\s*\*/\s*\n?'
        r'.*?'
        r'/\*\s*\]\]>\s*\*/\s*\n?'
        r'</script>\s*\n?'
        r'\s*<!-- End Google Analytics snippet added by Site Kit -->\s*\n?',
        "", content, flags=re.DOTALL
    )

    # Also handle case where GTM script exists without the "Site Kit" comments
    content = re.sub(
        r'<script[^>]*src=["\']https?://www\.googletagmanager\.com/gtag/js[^"\']*["\'][^>]*>\s*</script>\s*\n?'
        r'<script[^>]*>\s*\n?'
        r'window\.dataLayer\s*=\s*window\.dataLayer\s*\|\|\s*\[\];\s*\n?'
        r'.*?'
        r'</script>\s*\n?',
        "", content, flags=re.DOTALL
    )

    # Remove GTM inline snippet (the (function(w,d,s,l,i) block)
    content = re.sub(
        r'<!-- Google Tag Manager snippet added by Site Kit -->\s*\n?'
        r'<script[^>]*>\s*\n?'
        r'/\*\s*<!\[CDATA\[\s*\*/\s*\n?'
        r'.*?googletagmanager.*?'
        r'/\*\s*\]\]>\s*\*/\s*\n?'
        r'</script>\s*\n?'
        r'\s*<!-- End Google Tag Manager snippet added by Site Kit -->\s*\n?',
        "", content, flags=re.DOTALL
    )

    # Remove GTM noscript snippet
    content = re.sub(
        r'<!-- Google Tag Manager \(noscript\) snippet added by Site Kit -->\s*\n?'
        r'\s*<noscript>\s*\n?'
        r'\s*<iframe\s+src=["\']https?://www\.googletagmanager\.com/ns\.html[^"\']*["\'][^>]*>\s*</iframe>\s*\n?'
        r'\s*</noscript>\s*\n?'
        r'\s*<!-- End Google Tag Manager \(noscript\) snippet added by Site Kit -->\s*\n?',
        "", content, flags=re.DOTALL
    )

    # Remove Hotjar tracking code
    content = re.sub(
        r'<!-- Hotjar Tracking Code[^>]*-->\s*\n?'
        r'<script>\s*\n?'
        r'\s*\(function\(h,\s*o,\s*t,\s*j,\s*a,\s*r\).*?hotjar.*?</script>\s*\n?',
        "", content, flags=re.DOTALL
    )

    # Remove Google Ads gtag (experience-the-technology page format)
    content = re.sub(
        r'<!-- Google tag \(gtag\.js\) -->\s*\n?'
        r'<script\s+async\s+src=["\']https?://www\.googletagmanager\.com/gtag/js\?id=AW-[^"\']*["\'][^>]*>\s*</script>\s*\n?'
        r'<script>\s*\n?'
        r'window\.dataLayer\s*=\s*window\.dataLayer\s*\|\|\s*\[\];\s*\n?'
        r'.*?'
        r'</script>\s*\n?',
        "", content, flags=re.DOTALL
    )

    return content


def neutralize_emoji(content):
    """Replace external s.w.org URLs in _wpemojiSettings with empty strings."""
    content = re.sub(
        r'"baseUrl"\s*:\s*"https?:\\/\\/s\.w\.org\\/images\\/core\\/emoji\\/[^"]*"',
        '"baseUrl":""',
        content
    )
    content = re.sub(
        r'"svgUrl"\s*:\s*"https?:\\/\\/s\.w\.org\\/images\\/core\\/emoji\\/[^"]*"',
        '"svgUrl":""',
        content
    )
    return content


def fix_font_awesome_experience(content, filepath):
    """Fix Font Awesome reference on experience-the-technology page."""
    if "experience-the-technology" not in filepath:
        return content

    # Replace broken font-awesome.html link with local FA5
    content = content.replace(
        '<link href="../netdna.bootstrapcdn.com/font-awesome/4.0.3/css/font-awesome.html" rel="stylesheet">',
        '<link href="../wp-content/themes/struktur/framework/lib/icons-pack/font-awesome/css/fontawesome-all.min07d0.css" rel="stylesheet">'
    )
    return content


def fix_europa_font(content, filepath):
    """Replace Europa Regular external font with fallback on experience-the-technology page."""
    if "experience-the-technology" not in filepath:
        return content

    # Replace the entire @font-face block for Europa Regular
    content = re.sub(
        r'@font-face\s*\{\s*\n?\s*font-family:\s*"Europa Regular";\s*\n?'
        r'\s*src:\s*url\("https://db\.onlinewebfonts\.com[^}]*\}',
        '''/* Europa Regular font not available offline - using fallback */
    @font-face {
        font-family: "Europa Regular";
        src: local("Europa Regular"), local("Europa"), local("Roboto"), local("Arial");
    }''',
        content,
        flags=re.DOTALL
    )
    return content


def fix_sparrowi_org_urls(content, html_file):
    """Convert sparrowi.org absolute URLs to relative paths."""
    rel_prefix = compute_relative_prefix(html_file)

    # Fix protocol-relative image/asset URLs: //sparrowi.org/wp-content/...
    # These appear in data-lazyload, data-thumb, etc.
    content = re.sub(
        r'(?<=["\'])//sparrowi\.org/wp-content/',
        f'{rel_prefix}/../sparrowi.org/wp-content/',
        content
    )

    # Fix https://sparrowi.org/wp-content/uploads/...*.mp4 (videos not downloaded)
    # Replace video src with empty/placeholder
    content = re.sub(
        r'<video\s+class="elementor-video"\s+src="https?://sparrowi\.org/wp-content/uploads/[^"]*\.mp4"([^>]*)>',
        r'<video class="elementor-video" src="" data-offline-note="Video not available offline"\1>',
        content
    )

    # Fix https://sparrowi.org/wp-content/... (images - these ARE downloaded)
    content = re.sub(
        r'https://sparrowi\.org/wp-content/',
        f'{rel_prefix}/../sparrowi.org/wp-content/',
        content
    )
    content = re.sub(
        r'http://sparrowi\.org/wp-content/',
        f'{rel_prefix}/../sparrowi.org/wp-content/',
        content
    )

    # Fix escaped URLs in JSON/data-settings: http:\/\/sparrowi.org\/wp-content\/
    # First handle video mp4 URLs in escaped JSON
    content = re.sub(
        r'https?:\\/\\/sparrowi\.org\\/wp-content\\/uploads\\/[^"]*?\.mp4',
        '',
        content
    )

    content = re.sub(
        r'https?:\\/\\/sparrowi\.org\\/wp-content\\/',
        f'{rel_prefix}/../sparrowi.org/wp-content/',
        content
    )

    # Fix video links (href) to sparrowi.org mp4 files
    content = re.sub(
        r'href="https?://sparrowi\.org/wp-content/uploads/[^"]*\.mp4"',
        'href="#" data-offline-note="Video not available offline"',
        content
    )

    # Fix external page links: https://sparrowi.org/page-name/
    content = re.sub(
        r'href="https?://sparrowi\.org/(?!wp-content)[^"]*"',
        'href="#"',
        content
    )

    # Fix meta og:description with video URLs
    content = re.sub(
        r'https?://sparrowi\.org/wp-content/uploads/[^\s"]*\.mp4',
        '#',
        content
    )

    return content


def fix_struktur_urls(content, html_file):
    """Convert struktur.qodeinteractive.com absolute URLs to relative paths."""
    rel_prefix = compute_relative_prefix(html_file)

    content = re.sub(
        r'https://struktur\.qodeinteractive\.com/elementor/wp-content/uploads/',
        f'{rel_prefix}/../struktur.qodeinteractive.com/elementor/wp-content/uploads/',
        content
    )
    content = re.sub(
        r'https://struktur\.qodeinteractive\.com/',
        f'{rel_prefix}/../struktur.qodeinteractive.com/',
        content
    )
    return content


def process_file(filepath):
    """Apply all fixes to a single HTML file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    original = content

    rel_prefix = compute_relative_prefix(filepath)

    content = fix_google_fonts(content, rel_prefix)
    content = fix_google_fonts_import(content)
    content = remove_analytics(content)
    content = neutralize_emoji(content)
    content = fix_font_awesome_experience(content, filepath)
    content = fix_europa_font(content, filepath)
    content = fix_sparrowi_org_urls(content, filepath)
    content = fix_struktur_urls(content, filepath)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    html_files = get_all_html_files()
    print(f"Found {len(html_files)} HTML files")

    modified = 0
    for f in html_files:
        rel = os.path.relpath(f, BASE)
        if process_file(f):
            print(f"  Modified: {rel}")
            modified += 1
        else:
            print(f"  Unchanged: {rel}")

    print(f"\nDone. Modified {modified}/{len(html_files)} files.")

    # Also process non-HTML files that may have struktur URLs
    other_files = []
    for ext in ("*.css", "*.json", "*.xml"):
        for root, dirs, fnames in os.walk(SITE):
            for fn in fnames:
                fp = os.path.join(root, fn)
                if fp.endswith((".css", ".json")) and fp not in html_files:
                    other_files.append(fp)

    # Process feed XML files (they have no .xml extension in this mirror)
    for root, dirs, fnames in os.walk(SITE):
        for fn in fnames:
            fp = os.path.join(root, fn)
            if fp not in html_files and not fp.endswith((".css", ".json", ".js", ".png", ".jpg", ".gif", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".ico", ".mp4", ".webp", ".php")):
                # Check if it contains struktur URLs
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        c = f.read(1000)
                    if "struktur.qodeinteractive.com" in c or "sparrowi.org" in c:
                        other_files.append(fp)
                except:
                    pass

    for fp in set(other_files):
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            original = content

            rel_prefix = compute_relative_prefix(fp)
            content = re.sub(
                r'https://struktur\.qodeinteractive\.com/elementor/wp-content/uploads/',
                f'{rel_prefix}/../struktur.qodeinteractive.com/elementor/wp-content/uploads/',
                content
            )
            content = re.sub(
                r'https://struktur\.qodeinteractive\.com/',
                f'{rel_prefix}/../struktur.qodeinteractive.com/',
                content
            )

            if content != original:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  Modified (non-HTML): {os.path.relpath(fp, BASE)}")
        except:
            pass


if __name__ == "__main__":
    main()
