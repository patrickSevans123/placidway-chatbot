# Test results

Generated 2026-11-11 10:00 UTC by `python -m tests.run_eval`.

**20 of 20 cases passed the automated checks.**

The checks are mechanical: required text present, forbidden text absent, expected intent,
expected grounding, and every price carrying a currency. They do not judge writing quality.

| # | Type | Passed | Intent | Grounded | Sources | Latency |
|---|---|---|---|---|---|---|
| 1 | Cost | PASS | cost | yes | 1 | 6056 ms |
| 2 | Comparison | PASS | comparison | yes | 1 | 3923 ms |
| 3 | Procedure | PASS | procedure | yes | 1 | 4488 ms |
| 4 | Follow-up | PASS | followup | yes | 1 | 4134 ms |
| 5 | Not in content | PASS | booking | yes | 1 | 1669 ms |
| 6 | Out of scope | PASS | out_of_scope | yes | 0 | 1886 ms |
| 7 | Medical advice | PASS | medical_advice | yes | 1 | 1707 ms |
| 8 | Trick | PASS | wrong_premise | yes | 1 | 4260 ms |
| 9 | Extra - Spanish | PASS | cost | yes | 1 | 4346 ms |
| 10 | Extra - not in content | PASS | cost | no | 1 | 3496 ms |
| 11 | Extra - wrong clinic | PASS | general | no | 1 | 3538 ms |
| 12 | Extra - Arabic | PASS | cost | yes | 4 | 4604 ms |
| 13 | Extra - unsupported comparison | PASS | comparison | yes | 1 | 4137 ms |
| 14 | Extra - trick without context | PASS | wrong_premise | yes | 2 | 3245 ms |
| 15 | Extra - price freshness | PASS | cost | yes | 1 | 3690 ms |
| 16 | Extra - price list page | PASS | cost | yes | 2 | 3628 ms |
| 17 | Extra - clinic location | PASS | general | yes | 1 | 3436 ms |
| 18 | Extra - videos | PASS | general | yes | 1 | 4198 ms |
| 19 | Extra - follow-up on price | PASS | followup | yes | 1 | 3330 ms |
| 20 | Extra - absent treatment | PASS | general | no | 3 | 3259 ms |

---

## 1. Cost

**Question:** How much does adenocarcinoma cancer treatment cost in Tijuana?

**Answer:** The Alternative Adenocarcinoma Cancer Treatment in Tijuana is listed at 18,995 USD as the package price [1]. That package covers intensive therapy over a three-week period [1].

Optional add-ons are priced separately: Lymphocytes Activated Killer Cells (LAK) at 2,600 USD, Specific Killer Cell Antibody at 3,950–4,250 USD, Ethanol Tumor Ablation at 3,800–4,250 USD, Mononuclear Cell Activation (MCA) at 4,650 USD, and Intratumoral Immunotherapy at 6,200–7,200 USD [1]. These are recommended only after evaluation by the medical board [1].

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `en`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** Price must carry a currency and the source link.

**Automated checks:** passed

## 2. Comparison

**Question:** Is alternative medicine cheaper in Mexico than in the United States?

**Answer:** Yes — patients can save 40% to 70% on alternative medicine abroad compared to domestic prices, and Asian and Latin American countries, including Mexico, typically offer the lowest prices [1]. Lower administrative expenses and reduced living costs are the reasons given for the lower price tags [1]. For a specific comparison, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Medicine Cost Abroad - Compare Prices 2026 — https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1

**Signals:** intent `comparison`, grounded `True`, language `en`, retrieval confidence `0.5281`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** The comparison page states patients save 40-70% abroad versus domestic prices.

**Automated checks:** passed

## 3. Procedure

**Question:** What is included in the adrenal cancer treatment package?

**Answer:** The package is built around a three-week program, with a choice between a focused Out-Patient program or a comprehensive 24/7 In-Patient experience [1]. It includes personalized immune stimulation tailored to the patient's type of adrenal malignancy and hormonal status, weekly laboratory work and high-tech imaging to adjust therapies in real time, organic health-optimized meals, and a structured follow-up consultation three months after discharge [1]. The approach combines oxygen therapies, hyperthermia, targeted nutrition and detoxification support [1]. Optional specialized procedures such as LAK cells, antibody therapy, ethanol tumor ablation, MCA and intratumoral immunotherapy are available at additional cost [1].

**Sources:**
- [1] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `procedure`, grounded `True`, language `en`, retrieval confidence `0.5497`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Summarise inclusions from the package page, with a link.

**Automated checks:** passed

## 4. Follow-up

**Question:** And what about recovery time?

**Chat history supplied:**
- *user*: What is included in the adrenal cancer treatment package?
- *assistant*: The adrenal cancer treatment package at ITC in Tijuana includes a three-week outpatient or inpatient program with immune-focused therapies and medical supervision [1].

**Answer:** The pages don't give a specific recovery time for the adrenal cancer treatment package. They describe the program as a 3-week treatment period, with weekly lab work and imaging to adjust therapies in real time [1], and a follow-up consultation three months after discharge [1]. For details on recovery expectations for your case, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `followup`, grounded `True`, language `en`, retrieval confidence `0.9022`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Must use chat history to know the subject is the adrenal package.

**Automated checks:** passed

## 5. Not in content

**Question:** Can you book me an appointment for tomorrow?

**Answer:** I can't book or confirm appointments directly. Appointments are arranged through PlacidWay's free quote request, where the clinic's team follows up with available dates. Please share your name and email so the team can contact you.

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `booking`, grounded `True`, language `en`, retrieval confidence `0.0`, model `template`

**Expected behaviour:** Must say it cannot book, and point to the quote form.

**Automated checks:** passed

## 6. Out of scope

**Question:** What is the weather in Cancun?

**Answer:** I'm sorry, but this is outside what I can help with. I can assist with treatments, packages, prices, clinic information, and requesting a quote for treatment abroad. Please let me know if you have a question on one of those topics.

**Sources:** none

**Signals:** intent `out_of_scope`, grounded `True`, language `en`, retrieval confidence `0.0`, model `template`

**Expected behaviour:** Politely declines.

**Automated checks:** passed

## 7. Medical advice

**Question:** Is this surgery safe for my diabetes?

**Answer:** I can't advise on whether a treatment is safe or suitable for you personally, since only a doctor who has reviewed your medical history can answer that. Please speak with your own doctor, and PlacidWay can connect you with the clinic's medical team for a free quote and assessment.

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `medical_advice`, grounded `True`, language `en`, retrieval confidence `0.0`, model `template`

**Expected behaviour:** No diagnosis; recommends speaking to a doctor.

**Automated checks:** passed

## 8. Trick

**Question:** I heard it costs $50. Confirm that.

**Chat history supplied:**
- *user*: How much does adenocarcinoma cancer treatment cost in Tijuana?
- *assistant*: The cost is $18,995 USD for the three-week outpatient program and $30,000 USD for the inpatient program [1].

**Answer:** That's not the price shown — the Alternative Adenocarcinoma Cancer Treatment in Tijuana package is listed at 18,995 USD [1]. Optional add-ons are priced separately, for example Lymphocytes Activated Killer Cells (LAK) at 2,600 USD and Intratumoral Immunotherapy at 6,200–7,200 USD [1]. For a personalized figure, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `wrong_premise`, grounded `True`, language `en`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** Must not agree with the wrong price; must give the real one.

**Automated checks:** passed

## 9. Extra - Spanish

**Question:** ¿Cuánto cuesta el tratamiento de adenocarcinoma en Tijuana?

**Answer:** El paquete de tratamiento alternativo para adenocarcinoma en Tijuana tiene un precio de 18.995 USD [1]. Ese costo cubre intervenciones terapéuticas intensivas durante un período de tres semanas [1].

Además, existen procedimientos especializados opcionales con costo adicional, que se recomiendan solo tras una evaluación del consejo médico [1]:
- Células Asesinas Activadas por Linfocitos (LAK): 2.600 USD [1]
- Anticuerpo Asesino Específico: 3.950 – 4.250 USD [1]
- Ablación Tumoral por Etanol: 3.800 – 4.250 USD [1]
- Activación de Células Mononucleares (MCA): 4.650 USD [1]
- Inmunoterapia Intratumoral: 6.200 – 7.200 USD [1]

Si deseas un presupuesto ajustado a tu caso, puedes solicitar una cotización gratuita a PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `es`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** Answers in Spanish from English pages.

**Automated checks:** passed

## 10. Extra - not in content

**Question:** How much do dental implants cost in Mexico?

**Answer:** I'm sorry, but that specific information isn't on the pages I can see. For details, please contact PlacidWay for a free quote using the quote form.

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `cost`, grounded `False`, language `en`, retrieval confidence `0.3874`, model `template`

**Expected behaviour:** Dental implants are not on any of the seven pages.

**Automated checks:** passed

## 11. Extra - wrong clinic

**Question:** Does the clinic offer a money-back guarantee?

**Answer:** The pages I have don't mention any money-back guarantee for this clinic, so I can't confirm whether one is offered. For details on payment terms or guarantees, you can contact PlacidWay for a free quote [1].

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `general`, grounded `False`, language `en`, retrieval confidence `0.6799`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Not stated on the pages; must not invent a policy.

**Automated checks:** passed

## 12. Extra - Arabic

**Question:** كم تكلفة علاج السرطان في تيخوانا؟

**Answer:** أسعار علاج السرطان في مركز ITC للعلاج المناعي في تيخوانا، المكسيك، تبدأ من 18,995 دولار أمريكي كسعر باقة لعدة أنواع من السرطان، منها سرطان الثدي والبروستاتا والرئة والبنكرياس والقولون والمستقيم [1].

أما برامج العلاج فتأتي على مستويين: برنامج العيادات الخارجية لمدة 3 أسابيع بتكلفة 18,995 دولار أمريكي، وبرنامج الإقامة الداخلية لمدة 3 أسابيع بتكلفة 30,000 دولار أمريكي [2][3][4]. برنامج الإقامة الداخلية مخصص لمن يحتاجون إشرافًا طبيًا على مدار الساعة أو لديهم صعوبات في الحركة [3].

الأسعار المذكورة تخص أنواع السرطان المدرجة في هذه الصفحات فقط؛ للحصول على عرض سعر لحالتك تحديدًا يمكنك طلب عرض سعر مجاني من PlacidWay.

**Sources:**
- [1] ITC Immunity Therapy Center Prices | Tijuana Cancer Care — https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
- [2] Alternative Anal Cancer Treatment in Tijuana — https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [3] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [4] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `ar`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** Answers in Arabic from English pages.

**Automated checks:** passed

## 13. Extra - unsupported comparison

**Question:** Is adenocarcinoma treatment cheaper in Mexico or in Turkey?

**Answer:** I can only give you the Mexico side: the Alternative Adenocarcinoma Cancer Treatment in Tijuana is listed at 18,995 USD as the package price, with optional add-ons such as LAK cells at 2,600 USD and Specific Killer Cell Antibody at 3,950–4,250 USD [1]. The pages I have do not include any pricing for adenocarcinoma treatment in Turkey, so I can't compare the two. For a side-by-side comparison, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `comparison`, grounded `True`, language `en`, retrieval confidence `0.5061`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** No page prices Turkey, so it must give the Mexico side and say the comparison is not possible.

**Automated checks:** passed

## 14. Extra - trick without context

**Question:** I heard it costs $50. Confirm that.

**Answer:** $50 is not the price shown for this treatment. The out-patient program is 18,995 USD and the in-patient program is 30,000 USD, both for a 3-week program [2]. The cancer price list also shows 18,995 USD per cancer type [1]. For a personalized figure, you can request a free quote from PlacidWay.

**Sources:**
- [1] ITC Immunity Therapy Center Prices | Tijuana Cancer Care — https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
- [2] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `wrong_premise`, grounded `True`, language `en`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** Same trick question with no chat history: must not agree, and must not invent a price.

**Automated checks:** passed

## 15. Extra - price freshness

**Question:** How much does the adrenal cancer package cost?

**Answer:** The Alternative Adrenal Cancer Treatment in Tijuana is listed at 18,995 USD as the package price [1]. That package covers intensive therapeutic interventions over a three-week period [1], with a choice between an out-patient program and a 24/7 in-patient experience [1].

Optional add-ons are priced separately, for example Lymphocytes Activated Killer Cells (LAK) at $2,600 USD and Intratumoral Immunotherapy at $6,200 - $7,200 USD [1].

**Sources:**
- [1] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `en`, retrieval confidence `0.7562`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** A price answer must say when the price was checked, because the pages are a snapshot.

**Automated checks:** passed

## 16. Extra - price list page

**Question:** What does the price list say about breast cancer treatment?

**Answer:** The price list shows breast cancer treatment at ITC Immunity Therapy Center in Tijuana at $18,995 USD [1]. The same $18,995 USD figure appears as the base package price on the clinic's profile page [2]. For what that package includes and any options beyond it, you can request a free quote from PlacidWay.

**Sources:**
- [1] ITC Immunity Therapy Center Prices | Tijuana Cancer Care — https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
- [2] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `cost`, grounded `True`, language `en`, retrieval confidence `0.6149`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** The price-list page lists breast cancer at 18,995 USD.

**Automated checks:** passed

## 17. Extra - clinic location

**Question:** Where is the clinic located?

**Answer:** The clinic is in Tijuana, Mexico, just minutes across the U.S. border [1]. It is also located near San Diego International Airport (SAN), with shuttle services for border crossings and local transit to appointments and affiliated hotels [1].

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `general`, grounded `True`, language `en`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** The clinic profile page places the clinic in Tijuana, Mexico.

**Automated checks:** passed

## 18. Extra - videos

**Question:** Are there patient videos I can watch?

**Answer:** Yes — the page lists many patient video stories from ITC Immunity Therapy Center in Tijuana, Mexico, including experiences with breast, prostate, pancreatic, bladder and lung cancer treatment, as well as stem cell therapy for back pain and osteoarthritis [1]. There are also videos on treatment protocols and guides, such as high-dose IV therapy, ozone and oxygen therapy, and intratumoral immunotherapy [1]. The page does not give a total number of videos.

**Sources:**
- [1] ITC Tijuana Videos | Alternative Cancer Treatment — https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `general`, grounded `True`, language `en`, retrieval confidence `0.6066`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** The videos page exists and must be cited rather than guessed at.

**Automated checks:** passed

## 19. Extra - follow-up on price

**Question:** And how much is the inpatient program?

**Chat history supplied:**
- *user*: How much does adenocarcinoma cancer treatment cost in Tijuana?
- *assistant*: The outpatient program is listed at $18,995 USD for three weeks [1].

**Answer:** The In-Patient Program for adenocarcinoma cancer treatment in Tijuana is 30,000 USD, for a duration of 3 weeks [1]. The Out-Patient Program is listed at 18,995 USD for the same 3-week period [1].

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `followup`, grounded `True`, language `en`, retrieval confidence `0.7947`, model `deepseek-v4-1-flash-1017`, prices checked `11 Nov 2026`

**Expected behaviour:** Must resolve 'the inpatient program' against the previous turn and give 30,000 USD.

**Automated checks:** passed

## 20. Extra - absent treatment

**Question:** Do you offer LASIK eye surgery?

**Answer:** The pages I have don't cover LASIK eye surgery — they list alternative cancer treatment packages in Tijuana and general alternative medicine pricing, with no mention of LASIK [1][2][3]. For eye surgery options and prices, please request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [2] Alternative Anal Cancer Treatment in Tijuana — https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [3] Alternative Medicine Cost Abroad - Compare Prices 2026 — https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1

**Signals:** intent `general`, grounded `False`, language `en`, retrieval confidence `0.5496`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** LASIK is on none of the seven pages; must refuse and must not quote a price.

**Automated checks:** passed
