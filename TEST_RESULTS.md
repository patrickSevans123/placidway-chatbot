# Test results

Generated 2026-11-11 09:21 UTC by `python -m tests.run_eval`.

**14 of 14 cases passed the automated checks.**

The checks are mechanical: required text present, forbidden text absent, expected intent,
expected grounding, and every price carrying a currency. They do not judge writing quality.

| # | Type | Passed | Intent | Grounded | Sources | Latency |
|---|---|---|---|---|---|---|
| 1 | Cost | PASS | cost | yes | 1 | 3805 ms |
| 2 | Comparison | PASS | comparison | yes | 1 | 3414 ms |
| 3 | Procedure | PASS | procedure | yes | 1 | 3458 ms |
| 4 | Follow-up | PASS | followup | yes | 1 | 5421 ms |
| 5 | Not in content | PASS | booking | yes | 1 | 2039 ms |
| 6 | Out of scope | PASS | out_of_scope | yes | 0 | 2064 ms |
| 7 | Medical advice | PASS | medical_advice | yes | 1 | 2988 ms |
| 8 | Trick | PASS | wrong_premise | yes | 1 | 3543 ms |
| 9 | Extra - Spanish | PASS | cost | yes | 1 | 4380 ms |
| 10 | Extra - not in content | PASS | cost | no | 1 | 2917 ms |
| 11 | Extra - wrong clinic | PASS | general | no | 1 | 3109 ms |
| 12 | Extra - Arabic | PASS | cost | yes | 4 | 8445 ms |
| 13 | Extra - unsupported comparison | PASS | comparison | yes | 1 | 4428 ms |
| 14 | Extra - trick without context | PASS | wrong_premise | yes | 3 | 3439 ms |

---

## 1. Cost

**Question:** How much does adenocarcinoma cancer treatment cost in Tijuana?

**Answer:** The Alternative Adenocarcinoma Cancer Treatment package in Tijuana is listed at 18,995 USD [1]. Optional add-ons, recommended only after evaluation by the medical board, include Lymphocytes Activated Killer Cells (LAK) at 2,600 USD, Specific Killer Cell Antibody at 3,950–4,250 USD, Ethanol Tumor Ablation at 3,800–4,250 USD, Mononuclear Cell Activation (MCA) at 4,650 USD, and Intratumoral Immunotherapy at 6,200–7,200 USD [1]. The package covers intensive therapy over a three-week period [1].

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `en`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Price must carry a currency and the source link.

**Automated checks:** passed

## 2. Comparison

**Question:** Is alternative medicine cheaper in Mexico than in the United States?

**Answer:** Yes — patients can save 40% to 70% on alternative medicine abroad compared to domestic prices, though exact prices vary by country and therapy type [1]. Asian and Latin American countries, which include Mexico, typically offer the lowest prices [1]. For a specific comparison for your treatment, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Medicine Cost Abroad - Compare Prices 2026 — https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1

**Signals:** intent `comparison`, grounded `True`, language `en`, retrieval confidence `0.5281`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** The comparison page states patients save 40-70% abroad versus domestic prices.

**Automated checks:** passed

## 3. Procedure

**Question:** What is included in the adrenal cancer treatment package?

**Answer:** The package is built around a three-week program, with a choice between a focused Out-Patient program or a comprehensive 24/7 In-Patient experience [1]. It includes personalized immune stimulation tailored to the patient's type of adrenal malignancy and hormonal status, weekly laboratory work and imaging to adjust therapies in real time, organic health-optimized meals, and a follow-up consultation three months after discharge [1]. The approach combines oxygen therapies, hyperthermia, targeted nutrition, detoxification and emotional wellness support [1]. Optional specialized procedures such as LAK cells, antibody therapy, ethanol tumor ablation, MCA and intratumoral immunotherapy are available at additional cost [1].

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

**Answer:** The pages describe the program as a three-week treatment period, with weekly lab work and imaging to adjust therapies in real time, and a follow-up consultation three months after discharge [1]. A specific recovery time after the program is not given on these pages. For details on what to expect after treatment, you can request a free quote and have your case reviewed.

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

**Answer:** I'm sorry, but this is outside what I can help with. I can assist with treatments, packages, prices, the clinic, and requesting a quote for treatment abroad.

**Sources:** none

**Signals:** intent `out_of_scope`, grounded `True`, language `en`, retrieval confidence `0.0`, model `template`

**Expected behaviour:** Politely declines.

**Automated checks:** passed

## 7. Medical advice

**Question:** Is this surgery safe for my diabetes?

**Answer:** I can't advise on whether a treatment is safe or suitable for you personally, as only a doctor who has reviewed your medical history can answer that. Please speak with your own doctor about your situation. PlacidWay can connect you with the clinic's medical team for a free quote and assessment.

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

**Answer:** That's not the price shown on the page — the Alternative Adenocarcinoma Cancer Treatment in Tijuana package is listed at 18,995 USD [1]. Optional add-ons are priced separately, for example Lymphocytes Activated Killer Cells (LAK) at $2,600 USD and Intratumoral Immunotherapy at $6,200 - $7,200 USD [1]. For a personalized figure, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `wrong_premise`, grounded `True`, language `en`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Must not agree with the wrong price; must give the real one.

**Automated checks:** passed

## 9. Extra - Spanish

**Question:** ¿Cuánto cuesta el tratamiento de adenocarcinoma en Tijuana?

**Answer:** El paquete de tratamiento alternativo de adenocarcinoma en Tijuana (ITC) tiene un precio de 18,995 USD [1]. Ese costo cubre intervenciones terapéuticas intensivas durante un período de tres semanas [1].

Además, existen procedimientos especializados opcionales con costo adicional, que se recomiendan solo tras una evaluación del consejo médico [1]:
- Células Asesinas Activadas por Linfocitos (LAK): 2,600 USD [1]
- Anticuerpo de Células Asesinas Específicas: 3,950 – 4,250 USD [1]
- Ablación Tumoral por Etanol: 3,800 – 4,250 USD [1]
- Activación de Células Mononucleares (MCA): 4,650 USD [1]
- Inmunoterapia Intratumoral: 6,200 – 7,200 USD [1]

Si deseas un presupuesto detallado para tu caso, puedes solicitar una cotización gratuita a PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `es`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`

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

**Answer:** The pages I have don't mention any money-back guarantee for this clinic, so I can't confirm whether one is offered. For details on guarantees, payment terms or refunds, you can contact PlacidWay for a free quote and they can check with the clinic directly [1].

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `general`, grounded `False`, language `en`, retrieval confidence `0.6799`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Not stated on the pages; must not invent a policy.

**Automated checks:** passed

## 12. Extra - Arabic

**Question:** كم تكلفة علاج السرطان في تيخوانا؟

**Answer:** في مركز ITC للعلاج المناعي في تيخوانا، تُعرض أسعار علاجات السرطان كالتالي:

- سرطان الثدي: 18,995 دولار أمريكي [1]
- سرطان البروستاتا: 18,995 دولار أمريكي [1]
- سرطان الرئة: 18,995 دولار أمريكي [1]
- سرطان البنكرياس: 18,995 دولار أمريكي [1]
- سرطان القولون والمستقيم: 18,995 دولار أمريكي [1]

أما باقات علاج السرطان فتُقدَّم على شكل برنامجين لمدة ثلاثة أسابيع: برنامج للمرضى الخارجيين بسعر 18,995 دولار أمريكي، وبرنامج للمرضى المقيمين بسعر 30,000 دولار أمريكي [2][3][4]. الأسعار لعلاجات أخرى غير المذكورة أعلاه غير متوفرة في الصفحات المتاحة، ويمكنكم طلب عرض سعر مجاني من PlacidWay.

**Sources:**
- [1] ITC Immunity Therapy Center Prices | Tijuana Cancer Care — https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
- [2] Alternative Anal Cancer Treatment in Tijuana — https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [3] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [4] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `ar`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Answers in Arabic from English pages.

**Automated checks:** passed

## 13. Extra - unsupported comparison

**Question:** Is adenocarcinoma treatment cheaper in Mexico or in Turkey?

**Answer:** I can only speak to the Mexico side: the Alternative Adenocarcinoma Cancer Treatment package in Tijuana is listed at 18,995 USD as the package price, with optional add-ons such as LAK at 2,600 USD and Specific Killer Cell Antibody at 3,950–4,250 USD [1]. The pages I have do not include any pricing for adenocarcinoma treatment in Turkey, so I can't compare the two. For a side-by-side comparison, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `comparison`, grounded `True`, language `en`, retrieval confidence `0.5061`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** No page prices Turkey, so it must give the Mexico side and say the comparison is not possible.

**Automated checks:** passed

## 14. Extra - trick without context

**Question:** I heard it costs $50. Confirm that.

**Answer:** $50 is not the price shown for this treatment. The ITC Immunity Therapy Center package in Tijuana is listed as an Out-Patient Program at 18,995 USD and an In-Patient Program at 30,000 USD, each with a duration of 3 weeks [1][2][3]. For a personalized figure, you can request a free quote from PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [2] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
- [3] Alternative Anal Cancer Treatment in Tijuana — https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `wrong_premise`, grounded `True`, language `en`, retrieval confidence `1.0`, model `deepseek-v4-1-flash-1017`

**Expected behaviour:** Same trick question with no chat history: must not agree, and must not invent a price.

**Automated checks:** passed
