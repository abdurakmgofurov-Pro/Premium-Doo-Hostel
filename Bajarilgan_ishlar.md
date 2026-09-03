# Bajarilgan ishlar jurnali

Sana: 2026-08-27

## 1. Moliyaviy audit (bir martalik, Excel + vizual hisobot)
- Exely Extranet → "Отчет по броням" bo'limidan 2022–2026 oralig'idagi
  1582 ta bronni yuklab oldim.
- Valyutani (UZS/USD) sotuv manbasi (kanal) bo'yicha aniqladim, chunki
  eksport faylida valyuta ustuni yo'q edi.
- Natija: 295 024 091,20 UZS (718 bron) + 20 276,92 USD (864 bron).
- "Документооборот → Сверка броней" bo'limidan Exely'ning o'z
  booking-engine komissiyasini (yagona aniqlangan xarajat turi) topdim:
  jami 224 386,70 UZS (iyul–sentyabr 2026).
- Excel fayl (`Premium_Doo_Hostel_Moliyaviy_Audit.xlsx`) va vizual
  audit hisoboti (Claude Artifact) tayyorlab, foydalanuvchiga yubordim.

## 2. Avtomatlashtirilgan dastur (ExelyMoliyaviyHisobot papkasi)
- `exely_report.py` — Playwright orqali saytga kirib, bronlar hisoboti
  va komissiya ma'lumotini avtomatik yig'ib, Excel hisobot yaratadigan
  modul (qayta ishlatiladigan funksiyalar: login, export, scrape, aggregate).
- `app.py` + `templates/dashboard.html` — fon rejimida har 15 daqiqada
  avtomatik yangilanadigan jonli veb-dashboard (Flask). KPI'lar, kanallar,
  oylik tendensiya, komissiya jadvali, "Excel yuklab olish" tugmasi.
- `config.json` — login/parol va sozlamalar (foydalanuvchi o'zi to'ldirishi kerak).
- Ikkalasi ham kredensiyalarsiz (login/parolsiz) sintaksis va asosiy
  funksiyalar bo'yicha test qilindi (Excel generatori haqiqiy fayl bilan
  ishladi; Flask server ishga tushdi va /api/data to'g'ri javob qaytardi).

## 3. Xarajatlar / kompaniyalar bilan hisob-kitob moduli
- `db.py` (SQLite) + `/transactions` sahifasi: qo'lda xarajat/daromad/kompaniya
  tranzaksiyasi qo'shish, ko'rish, o'chirish. Dashboard'dagi "To'liq moliyaviy
  natija" jadvali shu ma'lumotni Exely tushumi bilan birlashtiradi.

## 4. Rasmiy Exely Public API'ga o'tish (foydalanuvchi talabi bilan)
- Foydalanuvchi Playwright/skreyping o'rniga haqiqiy API integratsiyasini
  so'radi. Exely Extranet → Property settings → API connections orqali
  yangi ulanish yaratildi ("Moliyaviy hisobot dasturi"): Read Reservation
  API + PMS API ruxsatlari bilan, client_id/client_secret oldim.
- `exely_api.py` — OAuth2 client_credentials orqali Exely Public API'ga
  ulanadigan klient (https://connect.hopenapi.com). Barcha bronlarni
  ro'yxatlab (pagination), har birining to'liq tafsilotini (tushum,
  valyuta, kanal, sana) oladi.
- `aggregate.py` — API'dan kelgan xom ma'lumotni valyuta/kanal/oy bo'yicha
  yig'adi. `report_excel.py` — shu asosda Excel hisobot yaratadi.
- `app.py` to'liq qayta yozildi: Playwright'siz, faqat rasmiy API asosida
  ishlaydi. Fon rejimida har 30 daqiqada avtomatik yangilanadi.

### Muhim texnik muammo va yechimi
- Ushbu muhitda API'ga ko'p sonli parallel so'rov yuborilganda ba'zan
  ulanishlar "abadiy osilib qolish" holatiga tushishi aniqlandi (bir nechta
  test orqali tasdiqlandi: sekin, lekin barqaror ishlagan holatlar ham,
  butunlay to'xtab qolgan holatlar ham kuzatildi).
- Yechim: so'rovlar 100 talik partiyalarga bo'lindi, har partiyadan keyin
  HTTP-sessiya yangilanadi, har partiya uchun "to'xtab qolish detektori"
  (30 soniya) ishlaydi, xato bo'lganlar uchun bitta qo'shimcha qayta urinish
  bosqichi qo'shildi. Natija: xatolik darajasi ~42%dan ~4%gacha tushdi,
  dastur endi hech qachon abadiy to'xtab qolmaydi.
- Yakuniy natija (2026-08-27, 17:35): 1729 bronning 1660 tasi (96%)
  muvaffaqiyatli yuklandi. Tushum: 278 661 117,20 UZS + 26 151,60 USD.

## 5. Ko'p foydalanuvchili tizim: login, huquqlar, bo'limlar
- Foydalanuvchi so'rovi: shunchaki dashboard emas, balki login/parol,
  foydalanuvchi huquqlari va alohida bo'limlarga ega to'liq veb-ilova.
- `auth.py` + `db.py`ga `users` jadvali qo'shildi: Super Admin (hammasiga
  huquqli, o'chirib bo'lmaydi), Admin (Foydalanuvchilar/Sozlamalardan
  tashqari hammasi), Alohida (custom — Super Admin har bir huquqni
  qo'lda belgilaydi: dashboard, bronlar, xarajatlarni ko'rish/tahrirlash,
  Excel yuklash).
- Yangi bo'limlar: `/bookings` (bronlar ro'yxati, qidiruv bilan),
  `/users` (foydalanuvchi boshqaruvi), `/settings` (API kalitlarini
  saytdan o'zgartirish).
- `templates/base.html` — umumiy yon panel (sidebar) navigatsiyasi,
  huquqlarga qarab ko'rinadigan/yashiringan bo'limlar bilan.
- Test qilindi: Super Admin barcha sahifalarga kira oldi; faqat
  "view_dashboard" huquqiga ega test foydalanuvchi /users va
  /transactions'dan to'g'ri 403 (ruxsat yo'q) oldi.

## Joriy holat
Tizim to'liq ishlamoqda: http://127.0.0.1:5000. Ishga tushirish:
`py -3 app.py` papka C:\Users\admin\ExelyMoliyaviyHisobot ichida.
Birinchi ishga tushirishda konsolda Super Admin login/paroli chiqadi.

## 6. Forma 2 (Moliyaviy natijalar to'g'risidagi hisobot)
Foydalanuvchi qarori: Exely'dan faqat tushum (savdo) avtomatik olinsin,
xarajatlar qo'lda kiritilsin, lekin haqiqiy buxgalteriya turkumlariga
guruhlangan holda.

- `db.py`: `CATEGORIES` endi 20 ta real buxgalteriya xarajat turkumi
  (Ish haqi, Kommunal, OTA komissiyasi, Ijara, Bank xizmat haqi, Soliq
  va h.k.), har biri `FORMA2_GROUPS`dan biriga bog'langan: tannarx,
  sotish, ma'muriy, boshqa operatsion, moliyaviy, soliq.
- `forma2.py`: `build_forma2(agg, manual)` — Exely tushumi (010-qator)
  va guruhlangan xarajatlardan standart Forma 2 tuzilmasini
  (010→030→040→050→060→080→090→100) hisoblaydi, UZS va USD alohida.
- Yangi `/reports` sahifasi (`view_reports` huquqi) — Forma 2'ni
  jadval ko'rinishida ko'rsatadi. Excel hisobotga ham "Forma 2" varag'i
  qo'shildi.
- Test qilindi: 5 000 000 UZS "Ijara haqi" xarajati to'g'ri "Ma'muriy
  xarajatlar" guruhiga tushib, 050/080/100-qatorlargacha to'g'ri
  kaskadlanishi tasdiqlandi.

### Muhim ochiq masala (foydalanuvchiga aytilgan)
Bu — **ichki (boshqaruv) hisobot**, rasmiy tasdiqlangan buxgalteriya
hujjati emas. Forma 1 (Balans) va Forma 3 (Pul oqimlari) hali yo'q —
ular uchun aktivlar, majburiyatlar, kapital va kassa qoldiqlari
ma'lumotlari kerak, bu tizim hozircha ularni yig'maydi. Rasmiy
taqdim etishdan oldin litsenziyalangan buxgalter tekshirib chiqishi
tavsiya etiladi.

## 7. Windows Task Scheduler orqali avtomatik ishga tushirish

Sana: 2026-08-28

- Reja.md'dagi oxirgi ochiq band ("kompyuter yoqilganda avtomatik ishga
  tushirish") bajarildi.
- `Register-ScheduledTask` orqali **"ExelyMoliyaviyHisobot"** nomli task
  yaratildi (foydalanuvchidan tasdiq olib, chunki bu tizim darajasidagi
  o'zgarish edi):
  - Trigger: foydalanuvchi "admin" Windows'ga login qilganda (AtLogOn).
  - Action: `pythonw.exe app.py` — konsol oynasiz, fonda ishga tushadi
    (WorkingDirectory: loyiha papkasi). `pythonw.exe` tanlandi (oddiy
    `python.exe` emas), chunki u qora konsol oynasini ko'rsatmaydi.
  - Sozlamalar: quvvat manbasidan qat'i nazar ishga tushadi, kompyuter
    band bo'lsa ham to'xtamaydi, xatoda 3 marta / 1 daqiqa oralig'ida
    qayta urinadi, vaqt chegarasisiz ishlaydi (Flask server doim tirik
    turishi kerak).
- `Get-ScheduledTask` bilan tekshirildi: task "Ready" holatida, trigger
  va action to'g'ri saqlangan.
- Eslatma: `app.py`dagi barcha fayl yo'llari (`config.json`, `data.db`,
  `secret_key.txt`, `reports/`) skript joylashuviga (`Path(__file__)`)
  nisbatan hisoblanadi, shuning uchun task qaysi joriy papkadan ishga
  tushishidan qat'i nazar to'g'ri ishlайdi.

### Joriy holat (yangilangan)
Reja.md'dagi barcha rejalashtirilgan bosqichlar bajarildi. Qolgan yagona
band — Exely komissiyasini rasmiy API orqali olish — API'da bunday
imkoniyat yo'qligi sababli doimiy cheklov bo'lib qoladi (hozirgi yechim:
"Xarajatlar" sahifasida qo'lda kiritish, bu allaqachon ishlayapti).

## 8. Dizaynni zamonaviy dark-theme uslubiga o'tkazish

Sana: 2026-08-28

- Foydalanuvchi so'rovi: eski (och rangli, PT Serif shrift bilan) dizayn
  yoqmadi — zamonaviy dasturlar (Linear/Vercel/Stripe uslubidagi)
  dark-theme dizaynga o'tkazish so'raldi.
- `templates/base.html` (barcha sahifalar shu yerdan meros oladi) va
  `templates/login.html` to'liq qayta dizayn qilindi:
  - Doimiy qorong'i palitra (avvalgi `@media prefers-color-scheme: dark`
    fallback emas — endi asosiy va yagona rejim), fon: chuqur
    qora-ko'k (#090b10) + subtile binafsha/moviy "aurora" gradient
    yoritqichlar orqa fonda.
    - Shrift PT Serif (jurnal uslubi) → Inter (IBM Plex Mono raqamlar
      uchun saqlab qolindi) — zamonaviy dashboard'larga xos.
  - Sidebar: gradient logotip belgisi, faol bo'lim binafsha-moviy
    gradient + porlash (glow) effekti bilan ajratiladi.
  - Tugmalar: "primary" gradient fon + soya (shadow-glow); kartalar
    (`.card`) yumshoq radius, nozik chegara va chuqur soya bilan.
  - Formalar/inputlar: fokusda accent rangli halqa (focus ring).
  - `dashboard.html`: og'ir oq chiziqli masthead border yumshoq
    kulrang chiziqqa almashtirildi, KPI raqamlari yorqinroq
    binafsha rangga o'zgartirildi (qorong'i fonda yaxshiroq
    o'qilishi uchun).
- Boshqa barcha sahifalar (`bookings.html`, `transactions.html`,
  `users.html`, `settings.html`, `reports.html`) o'zgartirilmadi —
  ular `base.html`dagi CSS o'zgaruvchilardan (`var(--...)`) foydalanadi,
  shuning uchun yangi palitra avtomatik qo'llanildi.
- Flask shablonlarni xotirada keshlashi sababli (debug=False bo'lgani
  uchun avtomatik qayta yuklanmaydi), server qayta ishga tushirildi
  (`taskkill` + `py -3 app.py`) — yangi dizayn darhol ko'rinishi uchun.
  `curl http://127.0.0.1:5000/login` orqali yangi CSS to'g'ri
  qaytayotgani tasdiqlandi.

## 9. Yon panel va tizim qobig'ini zamonaviy SaaS uslubiga o'tkazish

Sana: 2026-08-28

- Foydalanuvchi namunaviy skrinshot yubordi (moliyaviy platforma
  dashboard'i) va aytdi: "faqat ranglar emas, tizim yon panellarini
  zamonavilashtir, shu rasmdagi dizaynga mos bo'lsin". Ya'ni maqsad —
  rang emas, sidebar/topbar TUZILMASINI zamonaviy fintech SaaS
  (Linear/Stripe uslubidagi) darajasiga ko'tarish.
- `templates/base.html` qayta qurildi:
  - **Yangi tepa panel (topbar)**: sidebar'dan alohida, har bir
    sahifa tepasida — chapda "Premium Doo · Moliyaviy hisobot tizimi"
    breadcrumb, o'ngda yashil nuqta bilan "Jonli" belgisi (sticky,
    shaffof/blur fon).
  - **Sidebar**: emoji ikonalar (📊🧾💵) o'rniga chiziqli SVG
    ikonalar (Feather-uslubidagi: grid, fayl-chek, hamyon, ustunli
    diagramma, foydalanuvchilar, tishli g'ildirak) bilan almashtirildi.
  - Brand blok endi ikki qatorli: gradient "P" belgisi + "Premium Doo"
    / kichik "MOLIYAVIY TIZIM" subtitle — namunadagi logotip blokiga
    o'xshab.
  - Bo'limlar "Asosiy" va "Boshqaruv" nomli guruh sarlavhalari ostida
    tartiblangan (avval faqat "Boshqaruv" nomlangan edi).
  - Faol bo'lim endi to'liq gradient pill emas, balki namunadagi kabi
    yumshoq binafsha rangli fon + chap tomonda ingichka vertikal
    urg'u chizig'i bilan ko'rsatiladi.
  - Foydalanuvchi bloki (pastda) qayta qurildi: doira avatar (F.I.Sh
    bosh harflari, masalan "Super Admin" → "SA", Jinja orqali
    avtomatik hisoblanadi) + ism/rol matni + faqat ikona (strelka)
    ko'rinishidagi "Chiqish" tugmasi — avvalgi to'liq matnli havola
    o'rniga.
- `templates/dashboard.html`: KPI kartalar namunadagi uslubga mos
  qayta qurildi — har bir karta endi mustaqil (chegarali, soyali)
  quti bo'lib, yuqori qatorida yorliq + rangli icon-badge (masalan
  "UZS tushum" — yashil badge + yuqoriga strelka, "USD tushum" —
  moviy-feruza badge + dollar belgisi, "Bekor qilish darajasi" —
  qizil badge + pastga strelka), pastda katta raqam va kichik izoh.
- Serverni qayta ishga tushirib (`taskkill` + `py -3 app.py`),
  `admin` hisobi bilan kirib (`curl` + cookie jar orqali) barcha
  sahifalar (/, /bookings, /transactions, /reports, /users,
  /settings) tekshirildi — barchasi xatosiz 200 status bilan
  yuklandi, avatar inisiallari to'g'ri hisoblanganini ("SA")
  tasdiqladim.

## 10. Sidebar "yo'qolish" bugi topildi va tuzatildi (sticky emas edi)

Sana: 2026-08-28

- Foydalanuvchi bir necha marta skrinshot yubordi: sidebar butunlay
  ko'rinmayapti, faqat tepa panel qolgan, kontent oynaning chap
  chekkasidan boshlanayotgandek edi. Server tomonidan qaytarilayotgan
  HTML/CSS `curl` orqali qayta-qayta tekshirildi — hammasi to'g'ri
  edi, sababi topilmadi.
- Taxmin qilish o'rniga **Playwright** (loyihada allaqachon o'rnatilgan
  edi) orqali haqiqiy Chromium brauzerda sahifani ochib, avtomatik
  skrinshot oldim — 1600px va 700px kengliklarda sidebar TO'G'RI
  ko'rinar edi.
- Foydalanuvchi keyingi xabarida aniqlashtirdi: "dashboard oynasini
  pastga surganimda yon panel ham qo'shilib surilyapti, yon panel
  qotib tursin". Playwright bilan sahifani pastga scroll qilib
  tekshirsam — **aynan shu muammo tasdiqlandi**: sidebar `position:
  sticky` emas edi, shuning uchun sahifa pastga skroll qilinganda
  sidebar butun sahifa bilan birga yuqoriga siljib, ko'rinishdan
  chiqib ketardi (faqat tepa panel `sticky` bo'lgani uchun u joyida
  qolardi). Foydalanuvchi yuborgan barcha "sidebar yo'q" skrinshotlari
  aslida — sahifa pastga skroll qilingan holatlar edi.
- Yechim: `.sidebar`ga `position: sticky; top: 0; height: 100vh;
  overflow-y: auto; align-self: flex-start;` qo'shildi (mobil
  breakpointda `position: static`ga qaytariladi). Playwright bilan
  sahifani 1200px pastga scroll qilib qayta tekshirdim — sidebar
  endi butun scroll davomida joyida sobit turadi.
- Shu bilan birga foydalanuvchi so'ragan "kontent oynani to'liq
  egallasin" talabi bo'yicha `.page`ning `max-width`i 1180px'dan
  1520px'ga oshirildi.

## 11. 3 tilli interfeys: Rus (standart) / Ingliz / O'zbek

Sana: 2026-08-28

- Foydalanuvchi so'rovi: interfeysni rus tiliga o'tkazish va 3 til
  (rus/ingliz/o'zbek) orasida almashtirish imkoniyatini qo'shish.
- Yangi `i18n.py` moduli yaratildi — barcha interfeys matnlari uchun
  markazlashtirilgan `TR` lug'ati (kalit → {ru, en, uz}), shuningdek
  `CATEGORY_I18N` (xarajat turkumlari nomlari), `GROUP_I18N` (Forma 2
  guruh nomlari) va `PERMISSION_I18N` (foydalanuvchi huquqlari nomlari)
  — bular bazada saqlangan qiymatlarni (masalan `category` ustuni)
  O'ZGARTIRMAYDI, faqat ularning KO'RINISHINI tarjima qiladi.
- `app.py`: `session['lang']` orqali til saqlanadi (standart — "ru"),
  `/set_language/<lang>` marshruti qo'shildi, `context_processor`
  orqali `t()`, `t_cat()`, `t_group()`, `t_perm()` funksiyalari va
  `T_JSON` (dashboard'ning JS qismi uchun to'liq tarjima lug'ati)
  barcha shablonlarga uzatiladi; `t_perm`/`t_cat`/`t_group` Jinja
  filter sifatida ham ro'yxatdan o'tkazildi (`|map('t_perm')` kabi
  ishlatish uchun). Flash xabarlar (login xatosi, foydalanuvchi
  qo'shildi, va h.k.) ham tarjima qilindi.
- `forma2.py`: har bir qatorga barqaror `key` (masalan `"f2.010"`)
  qo'shildi — shablon endi qattiq yozilgan o'zbekcha matn o'rniga
  `t(row.key)` chaqiradi. Excel hisobot hozircha o'zbek tilida qoladi
  (o'zgartirilmadi — alohida so'ralmagan).
- Barcha shablonlar (`base.html`, `login.html`, `dashboard.html`,
  `bookings.html`, `transactions.html`, `users.html`, `settings.html`,
  `reports.html`) qattiq yozilgan o'zbekcha matnlardan `{{ t('...') }}`
  chaqiruvlariga o'tkazildi. `dashboard.html`da JS orqali qurilgan
  qismlar (KPI yorliqlari, jadval sarlavhalari, grafik izohlari)
  `window.T` global obyektidan foydalanadi (`base.html` `<head>`ida
  `{{ T_JSON }}` orqali inject qilinadi).
- **Muhim tuzatish**: `transactions.html`da `{% for t in transactions %}`
  sikli global `t()` tarjima funksiyasini soyalab (shadow) qo'yayotgan
  edi — sikl ichida `t('common.income')` chaqirilganda aslida
  `t()` funksiyasi emas, joriy tranzaksiya obyekti chaqirilib, xato
  berardi. Sikl o'zgaruvchisi `tx`ga o'zgartirildi.
- Topbar'ga til almashtirgich qo'shildi (RU/EN/UZ tugmalari, joriy til
  ajratib ko'rsatiladi), login sahifasiga ham xuddi shunday alohida
  til tugmalari qo'shildi (u `base.html`ni meros olmaydi).
- Playwright orqali tekshirildi: standart til — rus (login va
  dashboard to'liq ruscha), EN va UZ'ga almashtirish ishlaydi,
  `/transactions`dagi kategoriya dropdown'i, `/users`dagi huquqlar
  ro'yxati va `/reports`dagi Forma 2 qator nomlari to'g'ri tarjima
  qilinganini, konsolda JS xatosi yo'qligini tasdiqladim.

## 12. Bronlarni o'sib boruvchi (incremental) sinxronizatsiya

Sana: 2026-08-28

- Foydalanuvchi so'rovi: har safar yangilanishda BARCHA bronlarni
  boshidan qayta yuklash o'rniga, dastur avvalgi ma'lumotlarni o'zi
  saqlab qolsin va faqat yangi qo'shilgan/o'zgargan bronlarni olsin.
  Bu ayni paytda avvalgi "yuklash juda uzoq davom etadi (15–40 daqiqa)
  va foydalanuvchiga to'xtab qolgandek ko'rinadi" muammosini ham
  yechadi.
- `exely_api.py`da `list_booking_numbers()` metodida `modified_from`
  parametri ALLAQACHON mavjud ekan (ishlatilmagan holda) — Exely API
  o'zi "faqat shu vaqtdan beri o'zgargan bronlar" so'rovini
  qo'llab-quvvatlaydi. `fetch_all_bookings()`ga `modified_from`
  parametri qo'shib, shu imkoniyat ishga tushirildi.
- `db.py`: yangi `bookings_cache` jadvali (har bir bron xom JSON
  holida, `number` bo'yicha PRIMARY KEY) va `sync_state` jadvali
  (oxirgi sinxronizatsiya vaqtini saqlash uchun) qo'shildi. Yangi
  funksiyalar: `upsert_bookings()`, `load_all_bookings()`,
  `get_sync_state()` / `set_sync_state()`.
- `app.py`ning `refresh_once()` funksiyasi qayta yozildi:
  - Oxirgi sinxronizatsiya vaqti (`bookings_last_sync`) DB'dan
    o'qiladi; agar mavjud bo'lmasa (birinchi ishga tushirish) — to'liq
    yuklash, aks holda faqat shu vaqtdan beri o'zgargan bronlar
    so'raladi (odatda bir necha soniyada tugaydi, 1700+ o'rniga
    bir nechta bron).
  - Yangi/o'zgargan bronlar `bookings_cache`ga upsert qilinadi, keyin
    hisobot BUTUN keshdagi to'plam asosida (`load_all_bookings()`)
    hisoblanadi — shuning uchun `aggregate.py`/`report_excel.py`ga
    hech qanday o'zgarish kerak bo'lmadi.
  - **Xavfsizlik qoidasi**: agar shu safar biror bron yuklashda xato
    bo'lsa, `bookings_last_sync` checkpoint ILGARI SURILMAYDI — aks
    holda xato bo'lgan bron "modifiedFrom" oralig'idan chiqib ketib,
    doimiy yo'qolib qolishi mumkin edi. Xato bo'lgan hollarda checkpoint
    eski holicha qoladi va keyingi sinxronizatsiyada avtomatik qayta
    uriniladi.
- Bu — bir martalik "narx": birinchi ishga tushirishda hali ham to'liq
  yuklash kerak (o'zgarishsiz avvalgidek ishlaydi), lekin SHUNDAN
  KEYIN barcha kelajakdagi yangilanishlar bir necha soniyada tugaydi.
- Server qayta ishga tushirilib, run_log.txt'da yangi
  "Bronlar API orqali TO'LIQ yuklanmoqda (birinchi marta)..." xabari
  to'g'ri chiqqani tasdiqlandi (chunki `bookings_cache` jadvali yangi
  qo'shilgani uchun bo'sh edi).

## 13. Forma 2 (010-qator) sof tushum tuzatildi + haqiqiy ishlaydigan incremental sinxronizatsiya

Sana: 2026-08-28

### Muammo 1: 010-qator "sof tushum" emas edi
- Foydalanuvchi: Forma 2'ning 010-qatori ("Mahsulot (xizmat)larni
  sotishdan sof tushum") buxgalteriya normasiga mos bo'lishi kerakligini
  ta'kidladi.
- Tekshirilganda aniqlandi: Exely'dan kelayotgan har bir bron uchun
  ikkita summa bor — `priceBeforeTax` (soliqsiz) va `priceAfterTax`
  (soliq bilan). `aggregate.py` hozirgacha `priceAfterTax`ni ishlatib
  kelgan — ya'ni "tushum" sifatida QQS/soliq BILAN summa hisoblangan,
  bu esa "sof tushum" ta'rifiga (soliqsiz) zid edi.
- Keshdagi 1746 bronning 699 tasida bu ikki summa farq qilishi
  (soliq qo'llanilgani) tasdiqlandi — demak xato nazariy emas, real
  raqamlarga ta'sir qilardi.
- Tuzatish: `aggregate.py`da `"revenue"` maydoni endi `priceBeforeTax`
  (soliqsiz, sof) qiymatidan olinadi. Bu o'zgarish dashboard, bronlar
  ro'yxati, kanal/oylik statistika va Forma 2 — barchasiga bir xilda
  qo'llaniladi (hammasi bitta `agg['revenue_by_currency']`dan keladi),
  shuning uchun butun tizim izchil "sof tushum" mantig'iga o'tdi.
  Excel hisobot hozircha alohida so'ralmagani uchun o'zgartirilmadi.

### Muammo 2: "incremental sinxronizatsiya" (11-bandda yozilgan) aslida ishlamas edi
- Ishga tushirilgandan keyin kuzatuv paytida aniqlandi: `modifiedFrom`
  parametri bilan ishga tushirilgan so'rov, bu parametrsiz so'rovga
  qaraganda BIRON MARTA HAM kamroq natija qaytarmadi.
- To'g'ridan-to'g'ri Exely API'ga qo'lda turli formatdagi
  (`...Z`, millisekundli, offset bilan, faqat sana) `modifiedFrom`
  qiymatlari bilan sinov so'rovlari yuborildi — barchasida natija
  bir xil (1000 tadan, filtrsiz holatdek) qaytdi. Xulosa: bu parametr
  bu API/tarif uchun serverda HECH QANDAY filtrlash qilmaydi
  (indamay e'tiborsiz qoldiriladi, xato ham bermaydi).
- **Yangi, haqiqatan ishlaydigan yechim** (checkpoint asosidagi eski
  usul butunlay olib tashlandi, `sync_state` jadvali va
  `get_sync_state`/`set_sync_state` o'chirildi):
  - Bron RO'YXATI javobi (`bookingSummaries`) — arzon (sahifalab,
    1000 tadan) — har safar TO'LIQ olinadi, lekin har bir yozuvda
    `number`, `status`, `modifiedDateTime` allaqachon bor.
  - Bu ro'yxat mahalliy keshdagi (`bookings_cache.modified_at`)
    qiymatlar bilan MIJOZ TOMONIDA solishtiriladi; faqat mos
    kelmagan (yangi yoki chindan o'zgargan) bronlar uchungina QIMMAT
    operatsiya — to'liq tafsilotni alohida so'rash — bajariladi.
  - Yangi `ExelyApiClient.list_booking_summaries()` va
    `fetch_bookings_by_number(numbers)` metodlari qo'shildi
    (`fetch_all_bookings()` shu ikkisi orqali qayta yozildi).
  - **Muhim nozik joy**: ro'yxat javobidagi va tafsilot javobidagi
    `modifiedDateTime` bir xil bron uchun ~1 soniyaga farq qilishi
    aniqlandi (Exely API'sining o'zidagi nomuvofiqlik). Shuning uchun
    `bookings_cache`ga endi alohida `modified_at` ustuni qo'shildi va
    u ATAYLAB har doim faqat RO'YXAT javobidan to'ldiriladi (tafsilot
    javobidan emas) — aks holda ikki xil manba solishtirilib, deyarli
    HAR BIR bron doim "o'zgargan" deb noto'g'ri aniqlanardi (birinchi
    sinovda 1746tadan 623 tasi shunday soxta "o'zgargan" chiqdi).
- Bu — yana bir bor **bir martalik** narx: `modified_at` ustuni yangi
  qo'shilgani uchun eski keshdagi yozuvlarda bu maydon bo'sh, shuning
  uchun birinchi ishga tushirishda deyarli barcha bronlar yana bir
  marta "o'zgargan" deb aniqlanib, to'liq qayta yuklanadi — biroq bu
  safar SHUNDAN KEYIN `modified_at` izchil (faqat ro'yxat manbasidan)
  saqlanadi va haqiqatan ham faqat chin o'zgarishlar aniqlanadigan
  bo'ladi.
- **Saboq**: kodda oldindan yozilgan (`modified_from` parametri kabi)
  narsani sinab ko'rmasdan "ishlaydi" deb taxmin qilib qo'yish xato
  edi — Playwright bilan brauzerni tekshirganidek, bu safar ham
  to'g'ridan-to'g'ri API'ga so'rov yuborib REAL xatti-harakatni
  tekshirish orqaligina haqiqiy sabab topildi.

## 14. Forma 1/3, Kassa-Bank, Xizmatlar, Oy yopish, davr filtrlari — katta bosqich

Sana: 2026-08-28

Foydalanuvchi so'rovi: Forma 1 (Balans) va Forma 3 (Pul oqimlari)ni ham
norma bo'yicha ishlaydigan qilish, kassa/bank prixod-rasxodini yuritish
(qoldiqlari bilan), barcha sahifalarda oy bo'yicha filtr, hisobotlarni
oyma-oy yopish, va xizmatlar (sotib olingan + sotilgan) moduli.
Boshlashdan oldin 4 ta aniqlashtiruvchi savol berildi (AskUserQuestion):
natija — kassa/bank BITTA umumiy hisobda (manba belgisi bilan), Forma 1
FAQAT kassa/bank qoldig'iga asoslangan (soddalashtirilgan), xizmatlar
moduli ham sotib olingan (xarajat) ham sotilgan (daromad) turlarini
qamrab oladi, yopilgan oy QULFLANADI (faqat Super Admin qayta ochadi).
Keyin foydalanuvchi 3 ta skrinshot yubordi (boshqa tizimning "Банк и
Касса · Cash Flow", "Закрытие месяца" va "Финансовые отчёты" sahifalari)
— dizayn TUZILMASI shulardan olindi (filtrli reyestr, ketma-ket oy
yopish + tekshiruv ro'yxati, tab'li hisobotlar + KPI kartalar), lekin
MAZMUN bizning (yagona mulk, ishlab chiqarishsiz hostel) tizimimizga
moslashtirildi — masalan ularning ish haqi hisob-kitobi, to'liq
Aktiv=Passiv balans tekshiruvi va bo'lim/ob'ekt filtrlari bizda yo'q
(chunki bu ma'lumotlar umuman yig'ilmaydi).

### Yangi ma'lumotlar bazasi jadvallari (`db.py`)
- `cash_transactions` — kassa/bank prixod-rasxodi (`source`: kassa/bank,
  `section`: operatsion/investitsion/moliyaviy — Forma 3 uchun,
  `category` — kod bilan, masalan "1001 — Mehmonlardan naqd/bank
  tushumi").
- `services` — xizmatlar (`direction`: purchased/sold); `summarize_
  transactions()` endi xizmatlarni ham avtomatik Forma 2'ga qo'shadi
  (sotib olingan → xarajat/boshqa_operatsion guruhi, sotilgan → daromad).
- `closed_months` — yopilgan oylar (ketma-ket, snapshot bilan).
- `exchange_rates` — oy oxiri uchun valyuta kursi (yopish tekshiruvida
  talab qilinadi).
- `app_settings` — boshlang'ich kassa/bank qoldig'i (UZS/USD) kabi
  kalit-qiymat sozlamalar.
- Barcha yangi jadvallar uchun CRUD + `get_cash_balance()` (boshlang'ich
  qoldiq + shu sanagacha kirim-chiqim), `summarize_cash_period()` (Forma
  3 uchun bo'lim bo'yicha yig'indi), `month_close_status()` / `month_
  checklist()` / `close_month()` / `reopen_month()` (ketma-ket yopish
  mantig'i — oldingi oylar yopilmagan bo'lsa keyingisi yopilmaydi;
  qayta ochish ham faqat ENG OXIRGI yopilgan oy uchun ishlaydi).

### Yangi hisobotlar
- `forma1.py` — soddalashtirilgan Balans: faqat "Pul mablag'lari
  (kassa+bank)" qatori; reports.html'da aniq eslatma bilan ("bu to'liq
  ikki tomoni teng Forma 1 emas", chunki asosiy vositalar/qarzlar/
  kapital bu tizimda yig'ilmaydi).
- `forma3.py` — Pul oqimlari: operatsion/investitsion/moliyaviy
  faoliyat bo'yicha tushum/chiqim/sof oqim, so'ng davr boshi/oxiridagi
  qoldiq (opening + net change = closing, Playwright bilan raqamli
  tasdiqlandi: 5 000 000 + 1 500 000 = 6 500 000).

### Yangi sahifalar
- `/cash` (Kassa/Bank) — filtrli reyestr (Hammasi/Kirim/Chiqim tab),
  3 ta balans kartasi (Kassa/Bank/Jami, UZS+USD), qo'shish formasi
  (kod+nom bilan turkum tanlash), yopiq oy uchun qulf belgisi.
- `/services` (Xizmatlar) — sotib olingan/sotilgan, avtomatik Forma
  2'ga qo'shiladi.
- `/period-close` (Oy yopish) — chapda oylar ro'yxati (holat: yopilgan/
  navbatda/navbat kutmoqda/hali tugamagan), o'ngda tanlangan oy uchun
  6 punktli tekshiruv ro'yxati (yopilmagan/navbat/tugagan/kurs
  kiritilgan/manfiy qoldiq yo'q/kod bor) + yopish tugmasi (barcha
  tekshiruvlar o'tgandagina faollashadi) + oy ko'rsatkichlari (yakuniy
  kassa qoldig'i).
- `/reports` qayta qurildi: 3 ta tab (OFR/Forma2, Balans/Forma1, Cash
  Flow/Forma3) + 4 ta KPI karta (Tushum, Sof foyda, Yalpi marja, Sof
  marja) — uchinchi skrinshotdagi tuzilmaga mos.
- `/settings`ga ikkita yangi blok: boshlang'ich kassa/bank qoldig'i,
  oylik valyuta kursi (jadval bilan, tarix saqlanadi).

### Davr (oy/yil) filtri — barcha sahifalarda
- `templates/_period_filter.html` — qayta ishlatiladigan Jinja include
  (oy + yil dropdown, o'zgarganda avtomatik submit qiladi).
  Dashboard, Bronlar, Xarajatlar, Kassa/Bank, Xizmatlar, Hisobotlar —
  barchasiga qo'shildi. `app.py`da umumiy `get_period()` /
  `bookings_for_period()` yordamchilari — bronlar RAW JSON'dan
  `arrival` sanasi oyiga qarab filtrlanadi (`aggregate.flatten()`
  qayta ishlatiladi), `db.list_transactions/services/cash_
  transactions` esa SQL `substr(date,1,7)` orqali filtrlanadi.
  Playwright bilan tasdiqlandi: 2026-may filtri 245 ta bron, 2026-yanvar
  filtri 0 ta bron qaytardi (Bronlar sahifasi bilan bir xil sonda).

### Oy yopish qulfini amalga oshirish
- `db.is_date_locked(date)` — shu sana tegishli oy yopilganmi. Barcha
  qo'shish/o'chirish marshrutlarida (`/transactions/add`, `/cash/add`,
  `/services/add` va ularning `/delete` variantlari) tekshiriladi —
  yopiq oyga tegishli bo'lsa, xatolik xabari bilan rad etiladi.
  Jadvallarda yopiq oy yozuvlari uchun 🔒 belgisi ko'rsatiladi
  (o'chirish tugmasi o'rniga).

### Yangi huquqlar
- `view_cash`, `manage_cash`, `view_services`, `manage_services`,
  `manage_period_close` — `db.ALL_PERMISSIONS`ga qo'shildi, "Alohida"
  rolidagi foydalanuvchilarga /users sahifasidan alohida beriladi.

### Tekshiruv (Playwright)
- Barcha yangi sahifalar (`/cash`, `/services`, `/period-close`,
  `/reports` uch tab bilan) login qilingan holda 200 status va
  konsolda xatosiz ochilishi tasdiqlandi.
- Real ma'lumot bilan sinov: boshlang'ich qoldiq (5 000 000 UZS / 200
  USD) kiritildi, joriy oy uchun kurs (12700) saqlandi, 1 500 000 UZS
  kassa kirimi va 50 000 UZS xizmat sotuvi qo'shildi — Forma 1
  (6 500 000 UZS jami aktiv) va Forma 3 (operatsion sof oqim
  1 500 000, yakuniy qoldiq 6 500 000) to'g'ri hisoblanganini
  tasdiqladim.
- Sidebar/tepa panel yangi bo'limlar ("Банк и Касса", "Услуги",
  "Закрытие месяца") bilan skrinshotda vizual tasdiqlandi — dizayn
  foydalanuvchi yuborgan namunalarga mos.

### Qasddan qamrab olinmagan (foydalanuvchiga aytilishi kerak)
- **Excel eksport** hozircha faqat Forma 2 va bronlar ro'yxatini
  o'z ichiga oladi — Forma 1/3, Kassa/Bank va Xizmatlar Excel
  hisobotiga hali qo'shilmagan.
- **"Из Excel" import** (skrinshotdagi kabi) qurilmadi — faqat qo'lda
  kiritish mavjud.
- Kassa/bank sahifasidagi "Объект/Подразделение" (bo'lim/filial) va
  "Курсовая разница" (valyuta qayta baholash) kabi maydonlar ataylab
  qo'shilmadi — bular ko'p filialli/ishlab chiqarish korxonalariga
  xos, bitta hostel uchun keraksiz murakkablik bo'lardi.

## 15. Bar/mini-bar moduli (2026-08-28)

### Nima so'ralgan
Mehmonxona xonasidagi bar (kofe va boshqa ichimlik/tovarlar) uchun
alohida hisobot: tovar sotib olinadi (tan narx), mehmonga ustiga foyda
qo'yib sotiladi (sotish narxi). Aniqlashtiruvchi savollar orqali
kelishildi: (1) zaxira (stock) miqdori avtomatik kuzatiladi, (2) sotuv
Kassa/Bank'ga avtomatik pul kirimi sifatida yoziladi, (3) narxlar bitta
doimiy katalogda saqlanadi (har safar qo'lda kiritilmaydi).

### Ma'lumotlar bazasi (`db.py`)
- `bar_products` — mahsulot katalogi: nomi, o'lchov birligi, tan narx,
  sotish narxi, valyuta, joriy zaxira (`stock_qty`).
- `bar_transactions` — har bir kirim (`restock`) yoki sotuv (`sale`):
  mahsulot (nomi ham snapshot sifatida saqlanadi — mahsulot keyinchalik
  o'chirilsa ham tarix buzilmaydi), miqdor, birlik narxi, summa, hisob
  (kassa/bank), bog'langan `cash_transaction_id`.
- `add_bar_transaction()` — narxni katalogdan oladi, zaxirani yangilaydi
  (sotuvda zaxira yetarli emasligini tekshiradi — `insufficient_stock`),
  va bir vaqtning o'zida `cash_transactions`'ga mos yozuv qo'shadi
  (kirim → xarajat, sotuv → daromad, ikkalasi ham "operatsion" bo'limda).
- `delete_bar_transaction()` — zaxirani teskari o'zgartiradi va bog'liq
  kassa yozuvini ham o'chiradi (ikkalasi bir-biriga qat'iy bog'langan).
- `delete_bar_product()` — agar mahsulotga tegishli tranzaksiyalar
  mavjud bo'lsa, `ValueError("product_in_use")` bilan rad etiladi
  (tarixni buzmaslik uchun).
- Ikkita yangi Kassa/Bank turkumi qo'shildi (`CASH_CATEGORIES`ga):
  "Bar/mini-bar savdosi" (kod 1003, daromad) va "Bar/mini-bar tovar
  xaridi" (kod 2006, xarajat) — shu orqali oy yopish tekshiruvidagi
  "operatsiyalarda Cash Flow kodi bor" bandi ham to'g'ri o'tadi.
- `view_bar` / `manage_bar` — yangi huquqlar (`ALL_PERMISSIONS`).

### Forma 2'ga bog'lanish — shu yerda bitta eski kamchilik ham tuzatildi
`summarize_transactions()`ga yangi `revenue_extra` maydoni qo'shildi —
bar SOTUVI va xizmat (services) SOTILGAN summasi shu yerga to'planadi;
bar KIRIMI (tovar xaridi) esa `by_group["tannarx"]`ga (tannarx guruhiga)
qo'shiladi. `forma2.py`da 010-qator (tushum) endi Exely tushumi +
`revenue_extra` yig'indisi sifatida hisoblanadi.
**Muhim topilma:** avvalgi kodda `services` (Xizmatlar) sahifasidagi
"sotilgan" xizmatlar summasi hisoblanardi (`summary["income"]`), lekin
`build_forma2()` bu qiymatni HECH QACHON o'qimasdi — ya'ni "sotilgan"
xizmatlar Forma 2'ning 010-qatorida ko'rinmasdi, Reja.md'dagi "avtomatik
Forma 2'ga qo'shiladi" degan yozuv amalda noto'g'ri edi. Bar modulini
to'g'ri ishlashi uchun bu yerni tuzatishga to'g'ri keldi — natijada bu
xizmatlar-sotuvi kamchiligi ham yon-bag'irda tuzatildi.
- Bar tannarxi "xarid usuli" (purchases method) bilan hisoblanadi:
  sotib olingan TOVARNING TO'LIQ summasi darhol tannarx sifatida
  yoziladi (faqat sotilgan qism emas) — chunki Forma 1 soddalashtirilgan
  (faqat kassa/bank, ombordagi tovar aktiv sifatida hisobga olinmaydi).
  Buning oqibati: katta miqdorda tovar sotib olingan oyda Forma 2 vaqtincha
  "zarar" ko'rsatishi mumkin, keyingi oylarda sotuvlar bilan tuzaladi.
  Foydalanuvchi buni bilishi kerak (bu — ataylab qilingan soddalashtirish,
  Forma 1'ning "faqat kassa" qarori bilan izchil).

### Interfeys
- `templates/bar.html` — yangi sahifa: ombordagi tovar qiymati kartasi,
  mahsulot katalogi jadvali (narxni `<details>/<summary>` orqali JS'siz
  tahrirlash), yangi mahsulot qo'shish formasi, kirim/sotuv formasi
  (mahsulot tanlanganda joriy zaxira ko'rsatiladi), operatsiyalar tarixi
  (yopiq oy uchun 🔒).
- `templates/base.html` — yangi SVG ikonka + "Мини-бар" bo'limi sidebar
  navigatsiyasiga qo'shildi (`view_bar` huquqiga qarab ko'rinadi).
- `app.py` — `/bar`, `/bar/product/add`, `/bar/product/<id>/edit`,
  `/bar/product/<id>/delete`, `/bar/add`, `/bar/<id>/delete` marshrutlari.
- `i18n.py` — to'liq `bar.*` tarjima blok (ru/en/uz), yangi Kassa
  turkumlari va huquqlar tarjimasi.

### Tekshiruv (Playwright)
- Mahsulot ("Kofe", tan narx 8000 / sotish 15000 UZS) qo'shildim, 20
  dona kirim qildim (zaxira 20, Kassa'da 160 000 UZS chiqim yozildi),
  3 dona sotdim (zaxira 17, Kassa'da 45 000 UZS kirim yozildi) — Forma
  2'da 010-qator 45 000, 020-qator 160 000 to'g'ri chiqdi.
- Zaxiradan ortiq sotishga urinish (999 dona) — "Недостаточно товара на
  складе" xatosi bilan rad etildi, zaxira o'zgarmadi.
- Mahsulotni operatsiya mavjud paytda o'chirishga urinish — "Нельзя
  удалить товар" xatosi bilan rad etildi.
- Narxni `<details>` formasi orqali tahrirlash (15000 → 16000) — marja
  foizi (%) avtomatik qayta hisoblandi.
- Uch tilda (ru/en/uz) sahifa to'liq tekshirildi — barcha matnlar
  to'g'ri tarjima qilingan.
- Oy yopish sahifasidagi "operatsiyalarda Cash Flow kodi bor" bandi
  bar tranzaksiyalari mavjud bo'lganda ham ✓ (yashil) bo'lib qoldi.
- Test ma'lumotlari (mahsulot + ikkita tranzaksiya + bog'langan Kassa
  yozuvlari) sinovdan so'ng to'liq tozalandi — baza hozir faqat haqiqiy
  foydalanuvchi ma'lumotlarini saqlaydi.

### Qasddan qamrab olinmagan
- Bar mahsuloti uchun sotuv narxini har safar qo'lda o'zgartirish
  imkoniyati yo'q (ataylab — foydalanuvchi "doimiy katalog" variantini
  tanladi); narx o'zgarsa, katalogdagi mahsulotni tahrirlash kerak.
- Bar ma'lumotlari Excel eksportga hali qo'shilmagan (Kassa/Xizmatlar
  kabi — yuqoridagi 14-bo'limdagi cheklovga qarang).

## 16. Summalarni o'qish oson formatlash + Дт/Кт (kontragentlar bilan hisob-kitob) va to'liq Forma 1 (2026-08-28)

### Summalarni formatlash
Barcha ko'rsatiladigan summalar endi mingliklarga bo'sh joy bilan
ajratiladi (masalan `200000` -> `200 000.00`):
- `app.py`da `money`/`qty` Jinja filtrlari qo'shildi, 8 ta shablondagi
  barcha `"%.2f"|format(...)` chaqiruvlari shu filtrlarga almashtirildi.
- Summa kiritish maydonlari (`cost_price`, `sale_price`, `amount`,
  `opening_uzs/usd`, `rate`) endi `type="number"` emas, `type="text"
  class="money-input"` — `base.html`ga qo'shilgan global JS yozayotganda
  avtomatik guruhlaydi, yuborishda bo'sh joylarni olib tashlaydi. Server
  tomonda ham `parse_amount()` orqali qo'shimcha himoya (JS ishlamasa ham).

### Дт/Кт (kontragentlar bilan hisob-kitob) — yangi modul (`/ledger`)
Foydalanuvchi skrinshot yubordi ("Ведомости Дт-Кт") va so'radi: xizmat
sotib olinganda kontragent bilan Dt/Kt shakllanishi, bu balansda ham
ko'rinishi, ustav kapitali va asosiy vositalar ham qo'shilishi kerak.
3 ta aniqlashtiruvchi savolga javob olindi: (1) manba — Xarajatlar +
Xizmatlar (ikkalasida ham kontragent+holat maydoni bor); (2) to'lov —
TO'LIQ, alohida to'lov yozuvlari (qisman to'lov ham mumkin); (3) asosiy
vositalar — to'liq ro'yxat (har biri alohida), ustav kapitali — Sozlamalarda
bitta summa.

- `db.py`: yangi `payments` (source_type/source_id/date/amount/currency/
  note) va `fixed_assets` (name/value/currency/purchase_date) jadvallari.
  "Xarajatlar"/"Xizmatlar"da yozuv "to'landi" deb belgilansa, avtomatik
  to'liq to'lov yozuvi qo'shiladi (status maydoni endi faqat yaratilish
  paytidagi boshlang'ich holat — keyingi to'lov/qisman to'lov FAQAT
  `/ledger` orqali). Eski (mavjud) "to'langan" yozuvlar uchun
  `_backfill_payments_for_paid()` — har ishga tushirishda xavfsiz
  (idempotent, faqat to'lov yozuvi yo'qlarga qo'shadi).
- Dt/Kt hisob-kitob mantiqi standart buxgalteriya amaliyotiga mos: xarajat/
  xizmat XARIDI = Kt (biz qarzdormiz), daromad/xizmat SOTUVI = Dt (bizga
  qarzdor); har bir to'lov manba yozuvining QARAMA-QARSHI qutbida
  hisoblanadi (Kt qarzni to'lash = Dt harakati). Har bir kontragent uchun
  ALOHIDA svernutoy (netted) qoldiq hisoblanadi, keyin umumiy debitorlik/
  kreditorlik yig'indisiga qo'shiladi.
- `/ledger` — kontragentlar bo'yicha davr boshi/oborot/davr oxiri Dt/Kt
  jadvali (skrinshotdagi tuzilmaga mos, lekin faqat bizning ma'lumot
  modelimizga tegishli — "Поставщики/Покупатели/Займы/Офис" kabi
  tegishli bo'lmagan tab'lar OLIB TASHLANDI, bitta umumiy jadval).
  UZS/USD tab'lari, oy/yil filtri.
- `/ledger/detail?name=...&currency=...` — bitta kontragentning barcha
  manba yozuvlari, har biri uchun to'langan/qolgan summa va (agar qoldiq
  bo'lsa) `<details>` ichida to'lov qo'shish formasi + to'lovlar tarixi
  (o'chirish imkoniyati bilan). Oy yopilgan bo'lsa to'lov qo'shib/
  o'chirib bo'lmaydi (`is_date_locked`).
- Yangi huquqlar: `view_ledger`, `manage_ledger`.

### Forma 1 — endi TO'LIQ ikki tomonlama balans
`forma1.py` qayta yozildi: Aktivlar (pul mablag'lari + debitorlik +
asosiy vositalar) = Majburiyat va kapital (kreditorlik + ustav kapitali +
"Taqsimlanmagan foyda"). Oxirgisi — davr BOSHIDAN tanlangan sanagacha
JAMLANGAN (kumulyativ) sof foyda, bitta oyning emas (`db.
summarize_transactions_upto()` + `app.cumulative_net_profit()` — yangi
funksiyalar, bookings arrival sanasi va tranzaksiya/xizmat/bar sanasi
bo'yicha "upto_date" filtrlaydi). "Balans farqi" qatori aktiv/passiv mos
kelmasa ko'rsatadi — buxgalter tekshiruvi kerakligini bildiradigan
signal, majburan "tenglashtirilmaydi" (halol taqdimot).
- `/settings`ga ikkita yangi blok: "Ustav kapitali" (UZS/USD, bitta
  summa) va "Asosiy vositalar" (nomi/qiymati/valyuta/sana bilan ro'yxat,
  qo'shish/o'chirish).
- Yo'l-yo'lakay: KPI "Tushum" kartasi endi Forma 2'ning 010-qatoridan
  (Exely + xizmat/bar sotuvi) olinadi, avval faqat Exely tushumi edi.
- Yo'l-yo'lakay: "Начальный остаток кассы/банка" tugmasidagi eski
  tarjima xatosi tuzatildi (rus tilida "Saqlash" turib qolgan edi,
  "Сохранить" bo'lishi kerak edi).

### Tekshiruv (Playwright)
Haqiqiy ma'lumotlar bazasiga migratsiyadan OLDIN backup olindi
(`data_backup_before_ledger_*.db`). Test stsenariysi: Tesla-Power MChJ'ga
1 000 000 (to'lanmagan) + 200 000 (to'langan) xarajat, Hirvilammi
Hannu'ga 300 000 (to'lanmagan) sotilgan xizmat qo'shildi:
- `/ledger`: Tesla-Power — davr boshi 0, oborot Dt 600 000/Kt 1 200 000,
  davr oxiri Kt 600 000 (200 000 avtomatik to'lov + keyin qo'shilgan
  400 000 qisman to'lov = 600 000 Dt oborot, 1 200 000 Kt oborotdan
  ayirilib 600 000 qoldi) — qo'lda hisoblab tekshirilib, to'g'ri chiqdi.
- Qisman to'lov (400 000) qo'shilgach, qoldiq 1 000 000 dan 600 000'ga
  tushdi — to'g'ri.
- Forma 1: Debitorlik 300 000, Asosiy vositalar 3 000 000, Ustav kapitali
  50 000 000, Taqsimlanmagan foyda avtomatik yangilandi (yangi
  tranzaksiyalar ta'sirida kamaydi) — barcha raqamlar qo'lda hisoblab
  tasdiqlandi.
- 3 tilda (ru/en/uz) `/ledger` va `/ledger/detail` to'liq tekshirildi.
- Test ma'lumotlari (tranzaksiyalar, xizmat, asosiy vosita, to'lovlar,
  ustav kapitali) to'liq tozalandi — baza asl (bo'sh) holatiga qaytdi,
  Forma 1/2 raqamlari tozalashdan oldingi asl qiymatlarga mos keldi.

### Qasddan qamrab olinmagan
- Kassa/Bank va Bar kontragentlari Дт/Кт reestriga KIRMAYDI — ular
  darhol pul harakati (naqd) deb hisoblanadi, qarz emas. Faqat
  Xarajatlar/Xizmatlar sahifasidagi (kelajakda to'lanadigan) yozuvlar
  kontragent hisob-kitobiga kiradi.
- Asosiy vositalar uchun amortizatsiya (eskirish) hisoblanmaydi — faqat
  sotib olingan qiymat bo'yicha ko'rsatiladi.
- Дт/Кт ma'lumotlari Excel eksportga hali qo'shilmagan.

## 17. Kunlik valyuta kursi + UZS/USD umumiy (kombinatsiyalangan) summa (2026-08-28)

### Nima so'ralgan
Foydalanuvchi "Курс доллара" skrinshotini yubordi (grafik + tarix jadvali
+ "Добавить курс" tugmasi) va so'radi: (1) kurs OYLIK emas, KUNLIK
yuritilsin; (2) UZS va USD alohida ko'rsatilgan joylarda ular yig'indisi
(bitta umumiy summa) ham ko'rinsin.

### Kunlik kurs (`/exchange-rate`)
- `exchange_rates` jadvali qayta qurildi: `year_month` (PK) o'rniga
  `date` (PK) — endi istalgan kunga kurs qo'yish mumkin. Eski
  o'rnatishlar uchun avtomatik migratsiya: mavjud oylik yozuvlar har oy
  OXIRGI kuniga ko'chiriladi (`init_db()`da, xavfsiz — faqat eski
  sxema aniqlansa ishga tushadi).
- `get_exchange_rate_on(upto_date)` — berilgan sanada AMALDA bo'lgan
  kurs: shu sanagacha kiritilgan ENG SO'NGGI yozuv (keyingi kurs
  kiritilmaguncha oldingi kurs "amalda" hisoblanadi — real hayotdagi
  kabi). Oy yopish tekshiruvidagi "kurs kiritilgan" bandi endi shu
  funksiyadan foydalanadi (`get_exchange_rate_on(month_end)`).
- `templates/exchange_rate.html` — yangi sahifa: SVG chiziqli/maydonli
  grafik (tashqi kutubxona ISHLATILMADI — hand-rolled JS, chunki
  dashboard'dagi boshqa grafiklar ham shunday, offline ishlashi kerak
  bo'lgan desktop dastur uchun mos), kvadratik Bezier silliqlash orqali
  egri chiziq, tarix jadvali (sana + kurs + o'chirish), `<details>`
  orqali ochiladigan qo'shish formasi. Faqat Super Admin (Sozlamalar
  bilan bir xil huquq darajasi, chunki oy yopishga bevosita ta'sir qiladi).
- Eski "Sozlamalar"dagi oylik kurs bo'limi olib tashlandi, o'rniga yangi
  sahifaga havola qo'yildi.

### UZS/USD umumiy (kombinatsiyalangan) summa
- Kassa/Bank sahifasi ("Всего денежных средств" kartasi) — endi
  qo'shimcha qator: "≈ X UZS" (Kassa+Bank UZS + (Kassa+Bank USD × joriy
  kurs)), agar kurs kiritilgan bo'lsa.
- Dashboard "Итоговый финансовый результат" jadvali — qo'shimcha qator
  "Итого (в UZS по курсу)" — UZS sof natija + USD sof natija × kurs.
  Bu qism JS'da (`window.EXCHANGE_RATE` server orqali inject qilingan)
  hisoblanadi, chunki jadvalning o'zi `/api/data` orqali client tomonda
  qayta chiziladi.
- Ikkalasida ham kurs topilmasa (hali birorta ham kiritilmagan bo'lsa),
  kombinatsiyalangan qator ko'rsatilmaydi (xato o'rniga sokin o'tkazib
  yuboriladi).

### Tekshiruv (Playwright)
Haqiqiy bazaga migratsiyadan oldin backup olindi
(`data_backup_before_daily_rate_*.db`). 6 ta kurs (2026-06-01 dan
2026-08-28 gacha, 12300 dan 12800 gacha) qo'shildi — grafik to'g'ri
chizildi (skrinshotga vizual solishtirib tasdiqlandi), jadval yangidan
eskiga tartiblangan holda to'g'ri chiqdi. Kassa'ga 2 000 000 UZS + 500
USD qo'shilgach, "≈ 8 400 000.00 UZS" (2 000 000 + 500×12800) to'g'ri
hisoblanganini qo'lda tekshirdim. Dashboard'da "Итого (в UZS по курсу)"
qatori 630 157 077 (296 596 117 + 26 059,45×12800) — qo'lda hisoblab
tasdiqlandi. Oy yopish sahifasidagi "Курс на конец месяца введён" bandi
kunlik kurs kiritilgach ✓ (yashil) bo'lib qoldi. 3 tilda (ru/en/uz)
tekshirildi. Barcha test ma'lumotlari (kurslar, kassa yozuvlari) to'liq
tozalandi.

### Qasddan qamrab olinmagan
- Bar va Дт/Кт (kontragent) modullaridagi USD summalar kombinatsiyalangan
  qatorga alohida qo'shilmagan — faqat Kassa/Bank va Dashboard'dagi
  asosiy joylarda qo'shildi (eng ko'p ishlatiladigan joylar).
- Kurs tarixi Excel eksportga hali qo'shilmagan.
