# Reel Paradise Charters - host-ready static site package

This package is a redesigned static website for Reel Paradise Charters based on the current live site structure and service lineup.

## Included pages
- `/` homepage
- `/about-us/`
- `/key-west-boat-charters/`
- `/dry-tortugas-charter-key-west/`
- `/dry-tortugas-shared-trip-key-west/`
- `/key-west-sandbar-charter/`
- `/key-west-snorkeling-charter/`
- `/light-tackle-family-fishing-in-key-west/`
- `/key-west-sunset-cruise/`
- `/custom-private-charter-key-west/`
- `/gallery/`
- `/book-a-charter/`
- `/contact/`
- `/faq/`

## SEO items included
- Unique page titles and meta descriptions
- Canonical tags
- Open Graph / Twitter tags
- JSON-LD schema for LocalBusiness, Service, BreadcrumbList, and FAQPage
- `robots.txt`
- `sitemap.xml`
- Legacy redirects for:
  - `/our-services/` -> `/key-west-boat-charters/`
  - `/dry-tortugas-boat-charter/` -> `/dry-tortugas-charter-key-west/`

## Before launch
1. Replace the placeholder gallery blocks with real images.
2. Add descriptive alt text to each image.
3. Update the contact form action to your actual form endpoint.
4. Add analytics / tag manager / Meta pixel.
5. Confirm every booking button should point to:
   https://fareharbor.com/reelparadisecharters/items/
6. If you want social icons in the footer, add real profile URLs.
7. Test redirects after DNS cutover.
8. Submit the sitemap in Google Search Console.

## Hosting
This package works well on:
- Netlify
- Vercel static hosting
- Cloudflare Pages
- traditional cPanel / Apache static hosting

For Apache, `.htaccess` is already included.
