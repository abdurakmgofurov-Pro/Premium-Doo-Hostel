# Loyiha: Exely Moliyaviy Dashboard

Maqsad: Premium Doo Hostel uchun Exely'ning rasmiy Public API'sidan real
vaqtda olingan tushum ma'lumotlarini + qo'lda kiritiladigan xarajat/
kompaniyalar bilan oldi-berdi ma'lumotlarini birlashtirib, jonli moliyaviy
hisobot beradigan veb-dastur.

Loyiha papkasi: `C:\Users\admin\ExelyMoliyaviyHisobot\`
Ishga tushirish: `py -3 app.py` (shu papka ichida) -> http://127.0.0.1:5000

## Reja (bosqichlar)

- [x] Exely Extranet'dan bronlar hisobotini avtomatik yuklab olish
      (dastlab Playwright bilan, keyin foydalanuvchi talabi bilan rasmiy
      Public API'ga o'tkazildi — quyiga qarang)
- [x] Valyutani aniqlash — API orqali to'g'ridan-to'g'ri `currencyCode`
      maydonidan (avvalgi taxmin qilish usuli endi kerak emas)
- [x] Statik Excel hisobot generatori (`report_excel.py`)
- [x] Jonli veb-dashboard (Flask, `app.py` + `templates/dashboard.html`)
      — har 30 daqiqada avtomatik yangilanadi
- [x] Xarajatlar / kompaniyalar bilan oldi-berdi moduli:
      - [x] Ma'lumotlar bazasi (SQLite, `db.py`)
      - [x] Veb-forma: xarajat/kompaniya tranzaksiyasi qo'shish, o'chirish (`/transactions`)
      - [x] Dashboard'da: Exely tushumi + qo'lda kiritilgan xarajatlar = to'liq natija
- [x] Rasmiy Exely Public API integratsiyasi (OAuth2, client_id/client_secret)
      — Playwright butunlay olib tashlandi
- [x] Tarmoq beqarorligiga chidamlilik: partiyalab yuklash + qayta urinish
      (xatolik darajasi ~42%dan ~4%gacha tushirildi)
- [x] Windows Task Scheduler orqali kompyuter yoqilganda avtomatik ishga tushirish
      (foydalanuvchi "admin" login qilganda `pythonw.exe` orqali konsolsiz fonda
      ishga tushadigan "ExelyMoliyaviyHisobot" task yaratildi, xatoda 3 marta
      qayta urinadi)
- [ ] Exely komissiyasi (booking-engine xarajati) — bu rasmiy API'da yo'q,
      hozircha "Xarajatlar" sahifasida qo'lda kiritish orqali qamrab olinadi
- [x] Zamonaviy dark-theme dizayn (Linear/Vercel/Stripe uslubida): sectioned
      sidebar, top bar, icon-badge'li KPI kartalar — sidebar `position: sticky`
      qilib tuzatildi (avval scroll qilganda ko'rinishdan yo'qolib qolardi)
- [x] 3 tilli interfeys (rus — standart, ingliz, o'zbek) — `/set_language/<lang>`
      orqali almashtiriladi, `i18n.py`da markazlashtirilgan
- [x] Bronlarni o'sib boruvchi (incremental) sinxronizatsiya — bron
      ro'yxati (arzon) bilan mahalliy kesh solishtirilib, faqat haqiqatan
      o'zgargan bronlarning to'liq tafsiloti (qimmat) qayta so'raladi
      (`bookings_cache` jadvali; Exely API'ning `modifiedFrom` parametri
      sinovda ishlamasligi aniqlangani uchun undan voz kechildi)
- [x] Forma 2 (010-qator) — tushum endi soliqsiz ("sof tushum", norma
      bo'yicha to'g'ri) hisoblanadi, avval soliq bilan hisoblanardi
- [x] Kassa/Bank moduli (`/cash`) — prixod-rasxod, kod bilan turkumlar
      (Cash Flow bo'limlari: operatsion/investitsion/moliyaviy), Kassa/Bank/
      Jami balans kartalari
- [x] Forma 1 (Balans) — SODDALASHTIRILGAN: faqat kassa/bank qoldig'i
      (asosiy vositalar/qarzlar/kapital yig'ilmaydi, buxgalter tomonidan
      tekshirilishi kerak bo'lgan ichki hisobot)
- [x] Forma 3 (Pul oqimlari) — operatsion/investitsion/moliyaviy faoliyat
      bo'yicha, davr boshi/oxiridagi qoldiq bilan
- [x] Xizmatlar moduli (`/services`) — sotib olingan (xarajat) va sotilgan
      (daromad), avtomatik Forma 2'ga qo'shiladi
- [x] Oyni yopish (`/period-close`) — ketma-ket (avvalgi oy yopilmasa
      keyingisi yopilmaydi), 6 punktli tekshiruv, yopilgan oy qulflanadi
      (faqat Super Admin va faqat ENG OXIRGI yopilgan oyni qayta ochadi)
- [x] Oy/yil filtri — Dashboard, Bronlar, Xarajatlar, Kassa/Bank, Xizmatlar,
      Hisobotlar sahifalarida umumiy davr tanlagich
- [x] Bar/mini-bar moduli (`/bar`) — mehmonxona xonasidagi bar (kofe va h.k.):
      mahsulot katalogi (tan narx + sotish narxi, doimiy), zaxira (stock)
      avtomatik hisoblanadi, kirim (tovar sotib olish) va sotuv (mehmonga
      sotish) operatsiyalari Kassa/Bank'ga avtomatik pul harakati sifatida
      yoziladi va Forma 2'ga tushum/tannarx sifatida qo'shiladi
- [x] Barcha summalar mingliklarga bo'sh joy bilan ajratib ko'rsatiladi
      (masalan 200000 -> 200 000) — hisobotlar, jadvallar va kiritish
      maydonlarida ham (yozayotganda avtomatik guruhlanadi)
- [x] Дт/Кт (kontragentlar bilan hisob-kitob) moduli (`/ledger`) —
      "Xarajatlar" va "Xizmatlar" sahifasidagi kontragent+holat
      maydonlaridan avtomatik shakllanadi: har bir manba yozuvi uchun
      alohida to'lov (payments) qo'shiladi (qisman to'lovlar ham
      qo'llab-quvvatlanadi), qoldiq har doim summa - to'lovlar sifatida
      hisoblab chiqariladi. Kontragentlar bo'yicha davr boshi/oborot/
      davr oxiri Dt/Kt jadvali + har bir kontragent uchun tafsilot sahifasi
- [x] Forma 1 (Balans) endi TO'LIQ ikki tomonlama: Aktivlar (pul
      mablag'lari + debitorlik + asosiy vositalar) = Majburiyat va kapital
      (kreditorlik + ustav kapitali + jamg'arilgan sof foyda). Asosiy
      vositalar va ustav kapitali "Sozlamalar"da qo'lda kiritiladi;
      debitor/kreditor — Дт/Кт modulidan avtomatik. "Balans farqi" qatori
      aktiv/passiv mos kelmasa buni ko'rsatadi (buxgalter tekshirishi kerak)
- [x] Kurs doskasi (`/exchange-rate`) — valyuta kursi endi OYLIK emas,
      KUNLIK (istalgan sanaga qo'yiladi, keyingi yozuvgacha amal qiladi):
      grafik (SVG, tashqi kutubxonasiz) + tarix jadvali + qo'shish/o'chirish.
      UZS/USD alohida ko'rsatilgan joylarda (Kassa/Bank kartasi, Dashboard
      "Итоговый" jadvali) endi kursga asoslangan UMUMIY (bitta) summa ham
      qo'shimcha ko'rsatiladi
- [x] Bar mahsuloti qo'shish/tahrirlash formasida "Foyiz (%)" maydoni —
      tan narx + foyiz kiritilsa sotuv narxi avtomatik hisoblanadi; sotuv
      narxi qo'lda o'zgartirilsa foyiz shunga qarab qayta hisoblanadi
      (faqat brauzerdagi JS hisob-kitobi, serverga alohida saqlanmaydi)
- [x] Bar moduli ikkiga bo'lindi: `/bar` — soddalashtirilgan TEZKOR SOTUV
      sahifasi (faqat mahsulot + miqdor + hisob, mehmonga sotish uchun),
      `/sklad` — mahsulot katalogi, zaxira qiymati va tovar KIRIMI
      (xarid/oprihodovaniye) shu yerga ko'chirildi. Ikkala sahifa ham
      sidebar'da alohida ko'rinadi (`view_bar`/`manage_bar` ruxsatlari bilan)
- [x] Forma 1/2/3 (Hisobotlar) jadvallariga UZS/USD ustunlaridan tashqari
      kunlik kursga asoslangan "Umumiy (kursda, UZS)" ustuni qo'shildi —
      Kassa/Bank va Dashboard'dagi kabi. Kurs kiritilmagan bo'lsa, ustun
      ko'rinmaydi va buning o'rniga eslatma chiqadi
- [x] Bar (`/bar`) tezkor sotuv formasi endi "savatcha" (bir nechta
      mahsulot bitta sotuvda): "+ Mahsulot qo'shish" bilan qator qo'shiladi,
      har bir qatorda mahsulot+miqdor, pastda jonli "Jami" summasi
      (valyuta bo'yicha alohida) ko'rinadi. Yuborilganda har bir qator
      alohida bar_transaction yozuvi sifatida saqlanadi (`/bar/sell`)
- [x] Bar sahifasidagi "Счёт" tanlovi endi "Naqd pul / Karta" deb
      ko'rinadi (ichki buxgalteriya atamasi "Касса/Банк" o'rniga) —
      Naqd pul tanlansa Kassaga, Karta tanlansa Bankka yoziladi. Bu
      faqat Bar sahifasida; Kassa/Bank va Sklad sahifalarida buxgalteriya
      atamalari ("Касса/Банк") saqlanib qoladi
- [x] Sklad sahifasi qayta ishlandi (foydalanuvchi ko'rsatgan
      "Склад и производство" tizimi uslubida, faqat mehmonxona bariga
      mos maydonlar bilan): ikkita tab ("Mahsulotlar" / "Kirimlar"),
      "+ Kirim" tugmasi orqali ochiladigan MODAL oyna (bir nechta
      mahsulot bitta kirim operatsiyasida — sana/yetkazib beruvchi/
      to'lov turi umumiy, har qatorda mahsulot+miqdor, jonli jami
      summasi), Kirimlar tarixi jadvalida qidiruv+filtr qatori
      (mahsulot, to'lov turi) va "X dan Y ko'rsatilmoqda" hisoblagich,
      o'chirish endi ✕ belgili ikonka tugma orqali (`/bar/restock`
      marshruti — eski `/bar/add` olib tashlandi)
- [x] UZS/USD alohida ko'rsatiladigan yana bir necha joyga (Dashboard'dagi
      USD tushum KPI kartasi, Kassa va Bank alohida kartalari, Sklad
      "Ombordagi tovar qiymati" kartasi) kursga asoslangan "≈ ... UZS"
      qo'shimcha qatori qo'shildi — Forma 1/2/3 va Jami kartadan tashqari
- [x] Dollar kursi endi O'ZBEKISTON MARKAZIY BANKI saytidan (cbu.uz,
      rasmiy JSON API) AVTOMATIK olinadi — har kuni fon jarayonida
      (bronlar sinxronizatsiyasi bilan bir vaqtda) o'sha kunning rasmiy
      kursi tekshiriladi va yo'q bo'lsa avtomatik saqlanadi. Shuningdek
      "Dollar kursi" sahifasida "Shu sana uchun Markaziy bank kursini
      olish" tugmasi bilan qo'lda ham (masalan orqaga qolgan sanalar
      uchun) olish mumkin; qo'lda raqam kiritish ham hali mavjud
- [x] Kurs MAJBURIY qilindi: Xarajatlar, Kassa/Bank, Xizmatlar, Bar
      (sotuv va kirim) sahifalarida — agar operatsiya sanasi uchun
      (yoki undan oldingi sana uchun) kurs hali kiritilmagan bo'lsa,
      operatsiya saqlanmaydi va aniq xabar bilan "Dollar kursi"
      sahifasiga yo'naltiriladi. Bronlar (Exely API'dan avtomatik
      keladigan) bu tekshiruvdan mustasno — ular kiritish emas
- [x] Butun tizimda (`.page` konteyner) 1520px maksimal kenglik va
      markazga tekislash olib tashlandi — sahifa tarkibi endi ekranning
      to'liq kengligini egallaydi, o'ng-chapda foydasiz bo'sh joy yo'q
- [x] "Boshlang'ich qoldiq" (Sozlamalar) endi Kassa va Bank uchun
      ALOHIDA kiritiladi (4 maydon: Kassa UZS/USD, Bank UZS/USD),
      birgalikda emas. Shu jarayonda MUHIM XATO topildi va tuzatildi:
      `get_cash_balance()` funksiyasi Kassa va Bank balansini alohida
      so'raganda ikkalasiga ham TO'LIQ boshlang'ich qoldiqni qo'shib
      yuborardi — natijada "Jami" karta, Forma 1'dagi "Pul mablag'lari"
      va Forma 3'ning "Davr boshidagi qoldiq"'i boshlang'ich qoldiqni
      IKKI MARTA hisoblardi. Yangi `get_cash_opening()` funksiyasi bilan
      tuzatildi va butun tizim bo'ylab (Kassa/Bank, Forma 1, Forma 3)
      tekshirilib tasdiqlandi
- [x] YAGONA KO'RSATISH VALYUTASI: topbar'da (til tanlagichi yonida)
      UZS/USD tugmasi qo'shildi. Tanlangan valyuta butun tizim bo'ylab
      KO'RISH (hisobot/jadval/karta) qismida qo'llaniladi — UZS va USD
      ENDI ALOHIDA USTUNLARDA ko'rsatilmaydi, faqat kursga asosan
      tanlangan valyutaga aylantirilgan BITTA summa ko'rinadi. Bu
      Dashboard (KPI, "To'liq moliyaviy natija", kanallar, oylik grafik),
      Kassa/Bank/Sklad kartalari, Hisobotlar (Forma 1/2/3) sahifalarida
      qo'llanildi. YANGI OPERATSIYA KIRITISH formalari (Xarajatlar,
      Kassa, Xizmatlar, Bar/Sklad) o'zgarmadi — ularda hali ham UZS/USD
      tanlash mumkin, chunki mehmon/yetkazib beruvchi qaysi valyutada
      to'lagan bo'lsa shunda kiritiladi. Дт/Кт (qarz reestri) ham
      o'zgarmadi — u haqiqiy qarz valyutasini ko'rsatishda davom etadi
      (currency tab orqali), chunki qarzning o'zi konvertatsiya qilinmasa
      ham to'g'ri. Excel eksport (report_excel.py) ham o'zgarmadi —
      u hali ham UZS/USD alohida ustunlarda
- [x] Mobil/kichik ekranlarda haqiqiy CSS xatosi tuzatildi: grid/flex
      ichidagi maydonlar (`min-width:0` yo'qligi sababli) uzun matn
      (masalan mahsulot nomi + qoldiq) borligida konteynerdan tashqariga
      chiqib ketardi — Kirim modalidagi "Yetkazib beruvchi", "To'lov
      turi" va pastki tugmalar mobilda kesilib qolardi. Butun tizimda
      (`form.form-grid`) va Bar/Sklad'ning maxsus qator-formalarida
      tuzatildi, 520px'dan tor ekranlarda formalar 1 ustunga tushadi
- [x] Sklad'dagi mahsulotlar katalogi endi jadval emas, KOMPAKT
      KARTALAR panjarasi (nomi, qoldig'i, tan narx/sotish narxi/foyiz —
      barchasi bitta kartada, gorizontal skroll shart emas) — telefonda
      1 ustun, kompyuterda bir necha ustun, ma'lumot hech qachon
      kesilib qolmaydi
- [x] Bar'dagi "Tezkor sotuv" kartasi kompyuterda chapga yopishib,
      keng ekranda bo'sh joy qoldirardi (680px qattiq cheklov) —
      680px o'rniga 980px'gacha kengaytirildi, "Hisob" va "Sotish"
      tugmasi endi yonma-yon (avval alohida to'liq qatorlarda edi)
- [x] Bar'da mahsulot tanlash endi dropdown (select) emas, balki
      bosiladigan kartochkalar (product-card uslubida) — har birida
      nomi, narxi (avval umuman ko'rinmasdi) va qoldig'i ko'rsatiladi.
      Kartochkani bosish savatga qo'shadi (yana bosilsa — miqdori +1),
      savatdagi qatorda miqdorni qo'lda ham o'zgartirish va ✕ bilan
      o'chirish mumkin; jami summa avtomatik yangilanadi. Qoldig'i
      tugagan tovar kartasi kulrang va bosib bo'lmaydigan holatda.
- [x] Dashboard, Hisobotlar (Forma 1/2/3) va Kassa/Bank zamonaviylashtirildi:
      - `base.html`ga umumiy KPI-karta komponenti (`.kpi`, `.kpi-icon`, rangli
        ikonkalar) va "kompozitsiya tasmasi" (`.comp-bar`/`.comp-legend`,
        nisbat ko'rsatadigan rangli chiziq) ko'chirildi — endi barcha uch
        sahifa bir xil uslubda.
      - Dashboard: "Oylik tendensiya" endi tekis CSS ustunlar o'rniga
        silliq SVG chiziq/soha grafik (hover'da oy/summa/bron soni ko'rinadi);
        "Kanallar bo'yicha" endi donut (doiraviy) diagramma + ro'yxat;
        "To'liq moliyaviy natija" katta rangli sof natija raqami + tannarx
        emas, tushum/xarajat nisbatini ko'rsatadigan tasma bilan; 4 ta
        taqsimot kartasi (Kanallar/To'lov usuli/Xona turi/Tarif) 2 ustunli
        panjarada — endi kamroq skroll qilinadi.
      - Hisobotlar: KPI qatoriga rangli ikonkalar qo'shildi; Forma 2'da
        "Tushum qanday taqsimlanadi" kompozitsiya tasmasi (Tannarx/Boshqa
        xarajat/Sof foyda) qo'shildi; sarlavha endi tab'ga mos o'zgaradi
        (avval doim "Forma 2" deb yozardi, F1/F3'da ham xato edi).
      - Kassa/Bank: balans kartalariga ikonka qo'shildi; Kassa/Bank nisbatini
        ko'rsatadigan kompozitsiya tasmasi qo'shildi.
      - Yon effekt sifatida topilgan mobil xato: donut-diagrammaning qattiq
        `min-width:200px` legendasi 2-ustunli panjaraning ustunini kerakidan
        keng qilib, qo'shni kartani ham 390px ekranda 11px chetga chiqarib
        yuborardi — panjara elementlariga `min-width:0` va 460px'dan tor
        ekranlarda legend uchun alohida qoida qo'shib tuzatildi.
- [x] Exely'ning rasmiy Public API'sida FAQAT 2 domen bor (Read Reservation —
      bronlar, biz shuni ishlatamiz; Content API — mulk/xona/tarif tavsifi).
      "Финансовый учёт" (xarajatlar) uchun rasmiy API yo'q — bu faqat Exely
      panelining o'z ichki moduli. Shuning evaziga bron ma'lumotining o'zida
      ishlatilmayotgan maydonlar aniqlandi va qo'shildi:
      - `aggregate.py`: `flatten()`ga room_type, rate_plan, nights (kalendar
        sanalar bo'yicha, soatlar emas — 20-may 14:00→21-may 12:00 = 1 kecha),
        adults, children, payment_method qo'shildi; `aggregate_bookings()`ga
        `by_room_type`, `by_rate_plan`, `by_payment_method`, `stay_stats`
        (o'rtacha kecha/mehmon, yakka/guruh/bolali bandlar soni) qo'shildi.
      - Dashboard'ga 4 ta yangi karta: "Xona turlari bo'yicha", "Tarif
        rejalari bo'yicha", "To'lov usuli bo'yicha (Exely)" (Kassa bilan
        solishtirish uchun — Karta/Naqd/OTA/AtArrival/BankCardGuarantee),
        "Turish muddati va mehmonlar".
      - Bronlar ro'yxatiga (/bookings) 4 ta yangi ustun: Xona turi, Kecha,
        Mehmonlar, To'lov usuli.
- [x] Exely'ning "Финансовый учёт → Расход за период → Экспорт в XLSX"
      orqali yuklab olingan faylni Xarajatlar'ga import qilish funksiyasi
      qo'shildi (/transactions/import): fayl yuklanadi → ustunlar (Дата,
      Статья, Наименование, ФИО, Сумма, Способ оплаты) kalit so'z bo'yicha
      avtomatik aniqlanadi → ko'rib chiqish sahifasida har bir Exely
      "Статья"si bizning turkumlardan biriga moslashtiriladi (admin tanlaydi,
      standart — "Boshqa operatsion xarajat") va barcha qatorlar preview
      jadvalida ko'rsatiladi (hali hech narsa saqlanmagan) → tasdiqlangach
      import qilinadi. Bir xil qatorni ikki marta import qilib qo'ymaslik
      uchun har bir qator (sana+summa+tavsif+kontragent)dan barmoq izi
      hisoblab, `exely_expense_imports` jadvalida saqlanadi — qayta yuklashda
      avtomatik "Import qilingan" deb belgilanib o'tkazib yuboriladi. Oy
      yopilgan yoki o'sha sanaga kurs kiritilmagan qatorlar ham alohida
      hisoblab, import xulosasida ko'rsatiladi.
- [x] Sklad'dagi "Kirim" (tovar sotib olish) endi Дт/Кт'da ham ko'rinadi:
      Kirim modaliga "To'lov holati" (To'langan / To'lanmagan) qo'shildi.
      "To'langan" bo'lsa — avvalgidek, Kassa/Bank'dan pul darhol chiqadi.
      "To'lanmagan" (qarzga) bo'lsa — tovar zaxiraga DARHOL qo'shiladi,
      lekin Kassa/Bank'dan pul chiqmaydi; buning o'rniga yetkazib
      beruvchi Дт/Кт'da kreditor (Kt) sifatida ko'rinadi, qisman/to'liq
      to'lovni keyinroq Дт/Кт orqali qo'shish mumkin (aynan Xarajatlar/
      Xizmatlar kabi). Buning uchun `bar_transactions` jadvaliga `status`
      ustuni va `payments` jadvaliga `bar_transaction` manba turi
      qo'shildi (xavfsiz avtomatik migratsiya bilan)
- [x] Sklad'dagi "Tovar kirimi" modal oynasidagi interfeys buzilishi
      tuzatildi (bar.html'dagi avvalgi xato bilan bir xil sabab: `<form>`
      elementining o'ziga `form-grid` klassi berilmagan edi)
- [x] "Boshlang'ich qoldiq" (Sozlamalar) endi QAYSI SANAGA tegishli
      ekanini ham ko'rsatadi ("suratga tushirilgan" sana). Faqat shu
      sanadan KEYINGI operatsiyalar qoldiqqa qo'shib boriladi — undan
      OLDINGI (orqaga sanalgan) operatsiyalar hisobga olinmaydi, chunki
      ular allaqachon boshlang'ich qoldiqning o'zida hisobga olingan
      deb faraz qilinadi

- [x] "Xizmatlar" (services) sahifasi butunlay "Xarajatlar"ga birlashtirildi
      (2026-09-01) — ikkalasi texnik jihatdan deyarli bir xil ishlar edi
      (bir xil to'lov holati, bir xil Дт/Кт mexanizmi, bir xil Forma 2'ga
      tushish), shuning uchun ikkita alohida sahifa o'rniga bitta "Xarajat/
      Daromad" sahifasi qoldirildi:
      - `services` jadvali butunlay o'chirildi (ma'lumot yo'q edi, migratsiya
        shart bo'lmadi) — `db.py`dagi `add_service`/`get_service`/
        `delete_service`/`list_services`, `/services*` route'lari (`app.py`),
        `services.html`, "Xizmatlar" navigatsiya bandi va unga tegishli
        huquqlar (`view_services`/`manage_services`) butunlay o'chirildi.
      - Muhim farq saqlab qolindi: eski "sotilgan xizmat" — oddiy daromad
        emas, balki Forma 2'ning 010-qatoriga (asosiy tushum) qo'shiladigan
        realizatsiya daromadi edi. Bu endi Xarajatlar sahifasida "Turi" =
        Daromad tanlanganda ko'rinadigan alohida turkum orqali saqlanadi:
        "Mehmonga xizmat sotish (asosiy tushum)" — shu turkum tanlansa,
        summa avtomatik 010-qatorga qo'shiladi (`db.SERVICE_REVENUE_CATEGORY`).
        Oddiy daromad uchun "Boshqa (operatsion bo'lmagan) daromad" turkumi
        bor — bu eskidek 010-qatorga qo'shilmaydi.
      - "Xarajatlar" formasida "Turi" (Xarajat/Daromad) tanlanganda "Turkum"
        ro'yxati endi avtomatik almashadi: Xarajat tanlansa — eski
        kategoriyalangan (Forma 2 guruhlariga mos) ro'yxat, Daromad
        tanlansa — yuqoridagi 2 ta yangi turkum ko'rinadi.

- [x] Forma 2'da "Segment bo'yicha foyda" kartasi qo'shildi (2026-09-01):
      Hostel foydasi va Bar/mini-bar foydasi endi ALOHIDA ko'rsatiladi,
      pastda ikkalasi qo'shilib "Jami" ham chiqadi (bu — hozirgi "Sof
      foyda" bilan bir xil, aniq mos keladi). Bar foydasi = faqat
      Bar/mini-bar savdosi minus tovar tannarxi (yalpi foyda) —
      `db.summarize_bar_segment()`; boshqa umumiy xarajatlar (ijara, ish
      haqi va h.k.) Bar segmentiga taqsimlanmaydi, to'liq Hostel tomonida
      qoladi. Rasmiy 010-100 qatorli Forma 2 jadvalining o'zi o'zgarmadi —
      bu yangi karta uning ustiga qo'shildi.
- [x] Butun tizim bo'ylab har bir sahifadagi asosiy jarayonni birma-bir
      qo'lda (Playwright orqali) sinab chiqdim: Dashboard, Bronlar qidiruv,
      Xarajatlar (xarajat + daromad + Exely import), Kassa/Bank, Sklad
      (mahsulot qo'shish, to'langan/to'lanmagan Kirim), Bar (kartochka
      orqali sotish), Дт/Кт (qarz yozuvi + qisman to'lov), Hisobotlar,
      Foydalanuvchilar (qo'shish/o'chirish), Dollar kursi, Sozlamalar —
      barchasi to'g'ri ishlayapti.
      - Shu jarayonda **jiddiy xato topildi va tuzatildi**: "O'chirishni
        tasdiqlaysizmi?" kabi barcha tasdiqlash oynalari (confirm()) UZ
        tilida UMUMAN ishlamas ekan! Sababi: `onsubmit="return confirm('{{
        t(...) }}')"` naqshida tarjima matni apostrof (masalan
        "o'chirasizmi") tutgan bo'lsa, brauzer HTML atributini o'qib
        entity'larni yechgandan keyin bu JS satrni sindirib, butun
        `onsubmit` ATRIBUTI umuman kompilyatsiya bo'lmay qolar edi — natijada
        forma HECH QANDAY so'rovsiz to'g'ridan-to'g'ri yuborilardi (delete
        tugmasi bosilganda darhol o'chib ketaverardi). Bu barcha "O'chirish"
        tugmalariga (Bar, Kassa, Kurs, Дт/Кт to'lov, Sozlamalar, Xarajatlar,
        Sklad, Foydalanuvchilar) tegishli edi. Tuzatish: endi matn
        `onsubmit`ning ICHIGA emas, `data-confirm="{{ t(...) }}"` alohida
        atributiga chiqariladi (Jinja buni oddiy HTML atribut sifatida
        to'g'ri escape qiladi) va `base.html`da bitta umumiy delegatsiyalangan
        `submit` listener shu atributni o'qib `confirm()`ni chaqiradi —
        apostrof qanday bo'lishidan qat'i nazar endi to'g'ri ishlaydi.

- [x] To'liq RBAC (Rollar va huquqlar) tizimi qurildi (2026-09-01) — referens
      skrinshotlar asosida: har bir foydalanuvchi endi tekis huquqlar
      ro'yxati o'rniga qayta ishlatiladigan **Rolga** biriktiriladi, har bir
      Rolda 7 ta modul (Dashboard/Bronlar/Xarajatlar/Hisobotlar/Kassa-Bank/
      Bar-Sklad/Дт-Кт) x 5 amal (Ko'rish/Yaratish/O'zgartirish/O'chirish/
      Eksport) matritsasi bor — faqat modulga haqiqatan mos amallar
      bosiladigan, qolganlari kulrang (`db.ROLE_MODULES`).
      - Yangi `roles` jadvali + yangi sahifa `/roles` (kartochka+modal,
        faqat Super Admin uchun) — 5 ta standart rol avtomatik yaratiladi:
        Administrator, Buxgalter, Bar/Sklad menejeri, Kuzatuvchi, Huquqsiz.
      - **Foydalanuvchilar, Sozlamalar, Dollar kursi, Oy yopish** — ataylab
        matritsaga KIRITILMAGAN, avvalgidek faqat yagona Super Admin
        hisobiga tegishli bo'lib qoladi (foydalanuvchi bilan kelishilgan).
      - `db.has_permission(user, module, action)` yangi imzo bilan qayta
        yozildi, `auth.permission_required(module, action)` ham shunga mos;
        `app.py`dagi 25 ta route decoratori va 6 ta ichki `can_manage`
        bayrog'i (`can_create`/`can_edit`/`can_delete` deb aniqroq bo'lindi)
        yangilandi.
      - Foydalanuvchilar sahifasiga yo'qolgan "Tahrirlash" imkoniyati
        qo'shildi (`db.update_user` avval yozilgan-u, route yo'q edi).
      - Login sahifasi referensdagidek ikki ustunli qilib qayta dizayn
        qilindi (chapda tizim haqida qisqacha, o'ngda kirish formasi) —
        barcha eski xatti-harakat (`?next=`, til almashtirish) saqlanib
        qoldi.
      - **Yon effekt sifatida topilgan va tuzatilgan xato**: yangi `/roles`
        oynasining formasida xuddi shu sessiyada ikki marta uchragan
        `form.form-grid` xatosi yana takrorlandi (klass `<form>`ning o'ziga
        emas, ichidagi `<div>`ga qo'yilgan edi) — natijada "Rol nomi"/
        "Tavsif" yorliqlari va maydonlari ustma-ust chiqib, butun oyna
        buzilgan ko'rinardi. Klassni to'g'ri joyga (`<form>` teg) ko'chirib,
        checkbox'lar uchun ham umumiy `form-grid input` qoidasidan (matn
        maydonlari uchun mo'ljallangan `width:100%` va h.k.) alohida
        chiqarib tuzatildi.
      - **Jiddiy voqea**: RBAC ishini amalga oshirish jarayonida (aniq
        sababi topilmadi — server bir necha marta qayta ishga tushirildi)
        haqiqiy "coca cola 0.5" mahsuloti va unga tegishli "firma 01"
        qarz yozuvi bazadan yo'qolib qoldi. Buni ishni boshlashdan oldin
        olingan zaxira nusxadan (`data_backup_before_rbac_...`) aniq
        tikladim (faqat shu 2 ta yozuv, boshqa hech narsaga tegilmadi) va
        keyingi bir necha qayta ishga tushirishda ma'lumot barqaror
        qolganini tasdiqladim. Xavfsizlik uchun shu ishdan oldin darhol
        zaxira olish odati (bu safar ham qo'llanilgan) aynan shuning
        uchun kerak edi.

## Muhim cheklovlar (eslatma)

- Kunlik kurs cbu.uz'dan internet orqali olinadi — internet uzilsa yoki
  cbu.uz javob bermasa, avtomatik olish shunchaki jim o'tkazib
  yuboriladi (xato chiqmaydi) va keyingi fon-jarayon aylanishida
  (taxminan har 20 daqiqada) qayta urinadi; "Dollar kursi" sahifasidagi
  tugma orqali istalgan vaqtda qo'lda ham qayta urinish mumkin.
  Dam olish kunlari uchun cbu.uz oxirgi ish kunidagi kursni qaytaradi —
  bu normal, majburiy tekshiruvni buzmaydi.
- Forma 1'dagi debitor/kreditor "Xarajatlar", "Xizmatlar" va Sklad
  "Kirim" (qarzga/to'lanmagan holatdagi) yozuvlaridan hisoblanadi.
  Kassa/Bank va Bar SOTUVI (mehmonga sotish) bunga kirmaydi — ular
  har doim darhol naqd pul harakati deb hisoblanadi (mehmon darhol
  to'laydi deb faraz qilinadi). Asosiy vositalar va ustav kapitali qo'lda kiritiladi,
  shuning uchun "Balans farqi" ko'pincha nolga teng bo'lmasligi mumkin —
  bu normal, hisobot rasmiy taqdim etishdan oldin buxgalter tomonidan
  tekshirilishi kerak.
- Excel eksport hozircha faqat Forma 2 va bronlar ro'yxatini o'z ichiga
  oladi — Forma 1/3, Kassa/Bank, Xizmatlar, Bar Excel hisobotiga hali
  qo'shilmagan (lekin ularning summalari Forma 2/3'ga to'g'ri qo'shiladi).
- Bar moduli sotib olingan (kirim) tovarning TO'LIQ summasini darhol
  tannarx sifatida hisoblaydi (sotilmagan zaxira Forma 1'da aktiv sifatida
  ko'rsatilmaydi, faqat `/bar` sahifasida ma'lumot uchun "Ombordagi tovar
  qiymati" kartasida ko'rinadi) — bu Forma 1'ning soddalashtirilgan
  (faqat kassa/bank) tuzilmasiga mos soddalashtirish.
- "Из Excel" import (boshqa tizim namunasida ko'rilgan) qurilmagan — faqat
  qo'lda kiritish mavjud.
- API kalitlari (client_id/client_secret) `config.json` faylida oddiy matn
  holida saqlanadi (foydalanuvchi shunday tanladi).
- Har bir yangilanishda API'dan ~4% bronlar tarmoq beqarorligi tufayli
  o'tkazib yuborilishi mumkin (keyingi yangilanishda tuzatiladi).
