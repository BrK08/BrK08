# BrK08 — Space 3D Profil Paketi 🚀

GitHub profil README'inin tamamı **özgün SVG varlıklardan** oluşuyor: süper kütleli
karadelik, halkalı gezegenler, takımyıldızlar, HUD cam paneller, SMIL animasyonları.
JavaScript yok, iframe yok — GitHub'ın camo proxy'si üzerinden sorunsuz çalışır.

## Dosyalar

| Yol | Açıklama |
|---|---|
| `README.md` | Profil sayfası (uzay temalı, 1012px ölçekli tipografi) |
| `assets/*.svg` | 21 adet animasyonlu SVG varlık (hero, bantlar, karadelik, paneller…) |
| `.github/workflows/space-autopilot.yml` | Günlük otomatik yenileme (Actions) |
| `.github/scripts/gen_snake.py` | Katkı grafiğini "Contribution Constellation"a çevirir |
| `.github/scripts/live_stats.py` | Canlı telemetri panelini API'den üretir |
| `preview.html` | Tarayıcıda yerel önizleme |

## Kurulum

1. `BrK08/BrK08` adlı **public** profil reposunun olduğundan emin ol.
2. Paket içeriğini reponun **ana dizinine** kopyala (mevcut dosyaların üzerine):
   `README.md`, `assets/`, `.github/`.
3. Commit + push. Birkaç saniye içinde `github.com/BrK08` adresinde görünür.

## Canlı veri — Space Autopilot ⚡

`space-autopilot.yml` her gün **02:00 UTC (05:00 İstanbul)** çalışır:

- `assets/snake.svg` → son 365 günün gerçek katkı grafiği (GraphQL API)
- `assets/live_stats_3d.svg` → repo / takipçi / yıldız / commit + dil dağılımı (REST API)

Bot değişiklik varsa otomatik commit eder. Elle tetiklemek için:
**Actions → Space Autopilot → Run workflow**. Gerekli tek izin `contents: write`
(workflow içinde tanımlı, ekstra secret gerekmez).

> İlk push'tan sonra panelde "..." görürsen endişelenme — workflow ilk çalışmasında
> gerçek sayılarla doldurur. İstersen Actions'tan bir kez elle çalıştır.

## Özelleştirme

- **Renk paleti:** `space_lib.py` (statik varlıklar) ve `.github/scripts/*.py`
  (otomatik paneller) başındaki sabitlerden değiştir.
- **Varlıkları yeniden üretmek:** `python3 gen_space_a.py`, `gen_space_b.py`,
  `gen_space_c.py` (çıktı: `build/assets/`).
- **Bölüm metinleri:** `gen_space_a.py` içindeki `SECTIONS` listesi.

## SSS

**Fontlar neden SVG içinde gömülü değil?** GitHub resimleri proxy'ler; dış font
yüklenemez. Bu yüzden sistem font yığınları (Segoe UI, Cascadia/Consolas) kullanılır —
her cihazda tutarlı görünür.

**Yazılar küçük mü geldi?** Artık değil: tüm tuval 1012px = GitHub'ın render
genişliği; %100 ölçekli çizilir, küçültme yok.

**Eski Aurora temalı dosyalar?** Git geçmişinde duruyor; yeni tema ile değiştirildi.
