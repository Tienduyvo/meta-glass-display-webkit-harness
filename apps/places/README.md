# Example app: `places` (GPS)

Save spots with their **GPS location**. Demonstrates the `geo` field type: in the add bar on
phone/desktop, tap **📍** to capture your current coordinates (`lat,lon`) via the browser
Geolocation API. In the detail view the location links out to a map.

- **Add / edit on phone or desktop** (you can't type on the glasses).
- **View + check off on the glasses**, hands‑free.

## Fields
- **Place** (`name`, text)
- **Location** (`location`, geo — 📍 capture)
- **Note** (`note`, text)

> Testing without moving: in Chrome DevTools → ⋮ → More tools → **Sensors**, override the location
> with a custom latitude/longitude.
