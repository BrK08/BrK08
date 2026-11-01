# 🚀 Aurora 3D Profile — Kurulum Rehberi

GitHub profilin için tasarlanmış **gerçek 3D görünüm** (izometrik küpler, SMIL
animasyonları, cam paneller, aurora gökyüzü) içeren hazır paket.
Bu rehberi izleyerek **5 dakikada** yayına alabilirsin.

---

## 📦 Paket İçeriği

| Dosya / Klasör | Ne işe yarar? |
|---|---|
| `README.md` | Yeni 3D profil sayfan — GitHub'da otomatik görünür |
| `assets/` | Tüm 3D SVG çizimler (21 adet, hepsi animasyonlu) |
| `assets/snake.svg` | İlk kurulumda "placeholder" görünür; ilk workflow çalışmasından sonra canlı katkı grafiğine dönüşür |
| `assets/live_stats_3d.svg` | Canlı telemetri paneli (repo, follower, yıldız, commit sayıları + dil grafiği). İlk kurulumda "boot" çerçevesi görünür; Aurora Autopilot çalışınca gerçek verilerle yeniden çizilir |
| `assets/trophies_3d.svg` | 3D kupa dolabı — Take Off Türk, TEKNOFEST 2026, Treysan, "17 & Shipping" |
| `.github/workflows/aurora-autopilot.yml` | Her gün yılanı VE telemetri panelini otomatik yenileyen GitHub Action |
| `.github/scripts/live_stats.py` | Telemetri panelini GitHub API'den aldığı **gerçek** verilerle çizen betik (saf Python, ek kurulum gerekmez) |
| `preview.html` | Push etmeden önce yerelde GitHub görünümünü test etmeni sağlar |
| `SETUP.md` | Bu rehber (repoya yüklemek zorunda değilsin) |

---

## ⚡ Hızlı Kurulum (Git ile — önerilen)

> Profil README'i sadece **kullanıcı adınla birebir aynı addaki** özel repoda
> (`BrK08/BrK08`) görünür. Repon zaten varsa bu adımı atla.

1. **Depoyu klonla**
   ```bash
   git clone https://github.com/BrK08/BrK08.git
   cd BrK08
   ```

2. **Eski README'ni yedekle** (istemiyorsan atla)
   ```bash
   cp README.md README.yedek.md
   ```

3. **Zip'i aç ve dosyaları kopyala**
   Zip içindeki `README.md`, `assets/`, `.github/`, `preview.html` dosyalarını
   klonladığın klasörün içine kopyala (üzerine yaz).

4. **Commit'le ve gönder**
   ```bash
   git add -A
   git commit -m "feat: Aurora 3D profile ✨"
   git push
   ```

5. **Aurora Autopilot'u çalıştır (bir kez)** — yılan + telemetri paneli canlansın:
   - GitHub → **BrK08/BrK08** → **Actions** sekmesi
   - Sol listeden **Aurora Autopilot** → **Run workflow** → yeşil **Run** butonu
   - ~1 dakika sonra `assets/snake.svg` ve `assets/live_stats_3d.svg` gerçek
     verilerinle otomatik yenilenir ve profilinde görünür.

Bitti! → **github.com/BrK08** sayfanı yenile. 🎉

---

## 🖥️ Git Yok mu? (Web Arayüzü ile)

1. **github.com/BrK08/BrK08** reposunu aç.
2. Zip'i bilgisayarında **aynı klasör yapısıyla** çıkart.
3. Sitede **Add file → Upload files** ile `assets` klasöründeki tüm SVG'leri sürükle
   (klasörü sürüklersen `assets/` yolu korunur).
4. `.github/workflows/aurora-autopilot.yml` için: repo kökünde **Add file → Create new file**,
   dosya adına `.github/workflows/aurora-autopilot.yml` yaz, zip'teki içeriği yapıştır.
   Aynı şekilde `.github/scripts/live_stats.py` dosyasını da oluştur ve zip'teki
   betiğin içeriğini yapıştır. Commit'le.
5. `README.md`'yi kalem (✏️) ikonuyla aç, zip'teki yeni `README.md` içeriğinin
   tamamını yapıştır, commit'le.

---

## 🔄 Aurora Autopilot Nasıl Çalışır?

- Workflow **her gün 05:00 Türkiye saati** (02:00 UTC) otomatik çalışır:
  1. **Platane/snk** aksiyonu `assets/snake.svg` dosyasını son katkı grafiğinle yeniden üretir.
  2. `.github/scripts/live_stats.py` betiği GitHub API'den **gerçek** verileri çeker
     (repo sayısı, follower, yıldız, son 12 ayın commit sayısı, dil dağılımı) ve
     `assets/live_stats_3d.svg` panelini Aurora stilinde yeniden çizer.
  3. İki dosya tek commit ile repoya eklenir.
- İstediğin an elle de çalıştırabilirsin: **Actions → Aurora Autopilot → Run workflow**.
- Bir gün güncellenmezse repo ayarlarında Actions'ın açık olduğundan emin ol:
  **Settings → Actions → General → Actions permissions → Allow all actions and reusable workflows**.
- Workflow repoya yazma yetkisi olan default token'ı kullanır (`secrets.GITHUB_TOKEN`);
  **ekstra bir secret tanımlamana gerek yok**.

### 💡 Neden bu yaklaşım "ilk" seviyede?
Popüler istatistik kartları (github-readme-stats, trophy, activity graph) ücretsiz
topluluk servisleridir ve sık sık **çöker veya kapanır** — o zaman profilinde kırık
resimler kalır. Bu pakette telemetri **tamamen kendi reponda**, kendi workflow'unda
üretilir: dış servisler kapalı olsa bile panelin **her gün** çalışır ve asla kırılmaz.

---

## 🛠️ Sık Sorulanlar

**SVG'ler profilimde görünmüyor.**
→ Dosya yolları `assets/....svg` şeklinde relative olmalı, repon adı kullanıcı
adınla birebir aynı olmalı (`BrK08/BrK08`) ve repo **public** olmalı.

**Telemetri panelinde "..." gözlüyor, sayılar ne zaman gelir?**
→ Bu "boot frame" kasıtlıdır: ilk **Aurora Autopilot** çalışmasında gerçek
sayılarla değişir. Actions'ı bir kez elle çalıştırman yeterli (yukarıdaki adım 5).

**Animasyonlar neden GitHub'da çalışıyor?**
→ Tüm animasyonlar SVG'nin yerleşik standardı olan **SMIL** ile yapıldı
(hareketli küpler, yıldızlar, akan ışık şeritleri, kupa parlamaları). JavaScript/iframe
gerekmez, GitHub'ın resim proxy'si (camo) SMIL'i sorunsuz geçirir.

**Metin/renk nasıl değiştirilir?**
→ En kolay yol: ilgili SVG dosyasını bir metin editöründe aç, değiştirmek
istediğin yazıyı ara ve düz metin olarak değiştir (ör. `YKS PREPARATION`).
Renk paleti: `#7C5CFF` mor, `#4F7CFF` mavi, `#38BDF8` cyan, `#2DD4BF` turkuaz,
`#34D399` yeşil.

**Yerelde nasıl önizlerim?**
→ Zip'i açtığın klasörde `preview.html` dosyasına çift tıkla — GitHub'daki
görünümü birebir simüle eder (internet bağlantısı ile dış servisler de görünür).

**Eski haline dönebilir miyim?**
→ Evet. Push öncesi yedeklediğin `README.yedek.md`'yi geri yükle ya da GitHub'da
commit geçmişinden (History) önceki sürümü geri yükle (revert/restore).

---

Hazırlanma: Kasım 2026 · Tasarım: Aurora 3D · Sahibi: Hüseyin Berk Balcı
