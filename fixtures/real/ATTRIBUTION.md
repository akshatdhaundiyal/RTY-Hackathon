# Real product photos: attribution and notice

These six images are photographs of Indian medicine strips that the team downloaded from the internet
(retailer and manufacturer product listings) during the Buildathon, on 18 Nov 2026. They are used
**only to show that MediGuard's reading pipeline works on real packaging**, not for any commercial purpose.

**The original source URL and licence of each image were not recorded.** We do not claim any licence
for them. The products, brand names, trademarks and photographs belong to their respective owners
(for example Micro Labs, GSK, Abbott, Sanofi, Sun Pharma and Glenmark). If you are a rights holder and want an image removed,
open an issue or contact the repository owner and it will be deleted.

| File | Product shown | Notes |
|---|---|---|
| `dolo650.jpeg` | Dolo-650 (Micro Labs) | Front of the strip. Renamed from `dolo500.jpeg`: the strip says 650 mg. |
| `crocin650.jpeg` | Crocin 650 (GSK) | Back of the strip; the expiry field is blank in the photo. |
| `brufen400.jpeg` | Brufen 400 (Abbott) | |
| `combiflam.jpeg` | Combiflam (Sanofi) | Faint retailer watermark visible. |
| `pantocid_dsr.jpeg` | Pantocid DSR (Sun Pharma) | Carries a "truemeds" retailer watermark. |
| `telma40.jpeg` | Telma 40 (Glenmark) | Carries a "PlatinumRx" retailer watermark. Resized to 1000 px wide from a larger download. |

How they were checked: each image was run on its own through the app's OCR and local model (see the README).
They are single-strip photos; a collage of several strips in one image reads poorly.

None of these images is needed to run the app or the tests. The demo scenarios use the synthetic images in `fixtures/`.
