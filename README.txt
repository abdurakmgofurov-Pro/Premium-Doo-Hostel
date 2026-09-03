EXELY MOLIYAVIY TIZIMI (ko'p foydalanuvchili veb-ilova)
==========================================================

Ishga tushirish:  py -3 app.py   (shu papka ichida)
Ochish:           http://127.0.0.1:5000

BIRINCHI KIRISH
-----------------
Birinchi marta ishga tushganda konsolda (qora oyna) Super Admin
login/parolini ko'rasiz, masalan:
  Login: admin
  Parol: (tasodifiy yaratilgan)
Buni saqlab qo'ying. Keyin /users sahifasidan xohlagan odamlar uchun
yangi hisoblar yarata olasiz.

BO'LIMLAR
-----------
- Dashboard (/)        — jonli tushum, kanallar, oylik tendensiya
- Bronlar (/bookings)  — barcha bronlar ro'yxati, qidiruv bilan
- Xarajatlar (/transactions) — qo'lda xarajat/daromad/kompaniya tranzaksiyasi
- Foydalanuvchilar (/users)  — FAQAT Super Admin: hisob qo'shish/o'chirish,
  har biriga alohida huquq berish
- Sozlamalar (/settings)    — FAQAT Super Admin: Exely API kalitlarini
  saytdan chiqmasdan o'zgartirish

HUQUQLAR TIZIMI
------------------
- Super Admin — hamma narsaga to'liq huquqli, boshqa hech kim uni o'chira olmaydi.
- Admin — Foydalanuvchilar/Sozlamalardan tashqari hamma narsaga huquqli.
- Alohida (custom) — Super Admin har bir foydalanuvchi uchun aynan qaysi
  bo'limlarni ko'ra olishi va tahrirlay olishini o'zi belgilaydi
  (Dashboard, Bronlar, Xarajatlarni ko'rish, Xarajat qo'shish/o'chirish,
  Excel yuklab olish).

SOZLASH
---------
API kalitlari va boshqa sozlamalar /settings sahifasida (Super Admin
sifatida kirib) o'zgartiriladi — config.json faylini qo'lda tahrirlash
shart emas.

MUHIM CHEKLOV
---------------
Bu tizim to'liq buxgalteriya (Forma 1/2/3) hisobotini bermaydi — faqat
Exely'dan tushum va qo'lda kiritilgan xarajatlarni birlashtiradi.
