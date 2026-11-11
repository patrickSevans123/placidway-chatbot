# Test results

Generated 2026-11-11 07:52 UTC by `python -m tests.run_eval`.

**9 of 12 cases passed the automated checks.**

The checks are mechanical: required text present, forbidden text absent, expected intent,
expected grounding, and every price carrying a currency. They do not judge writing quality.

| # | Type | Passed | Intent | Grounded | Sources | Latency |
|---|---|---|---|---|---|---|
| 1 | Cost | PASS | cost | yes | 1 | 17814 ms |
| 2 | Comparison | FAIL | comparison | no | 1 | 35744 ms |
| 3 | Procedure | PASS | procedure | yes | 1 | 36992 ms |
| 4 | Follow-up | PASS | followup | yes | 1 | 30965 ms |
| 5 | Not in content | PASS | booking | yes | 1 | 18187 ms |
| 6 | Out of scope | PASS | out_of_scope | yes | 0 | 23365 ms |
| 7 | Medical advice | PASS | medical_advice | yes | 1 | 32638 ms |
| 8 | Trick | PASS | wrong_premise | yes | 2 | 43189 ms |
| 9 | Extra - Spanish | PASS | cost | yes | 1 | 51188 ms |
| 10 | Extra - not in content | PASS | cost | no | 1 | 24272 ms |
| 11 | Extra - wrong clinic | FAIL | general | yes | 2 | 12605 ms |
| 12 | Extra - Arabic | FAIL | cost | yes | 1 | 6863 ms |

---

## 1. Cost

**Question:** How much does adenocarcinoma cancer treatment cost in Tijuana?

**Answer:** The cost for Alternative Adenocarcinoma Cancer Treatment in Tijuana is $18,995 USD for the Out-Patient Program (3 weeks) and $30,000 USD for the In-Patient Program (3 weeks) [1]. Optional specialized procedures and additional services may incur extra charges [1]. For a personalized quote, you can request a free quote through PlacidWay.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `en`, retrieval confidence `0.9958`, model `gh/gpt-4.1`

**Expected behaviour:** Price must carry a currency and the source link.

**Automated checks:** passed

## 2. Comparison

**Question:** Is alternative cancer treatment cheaper in Mexico or in the United States?

**Answer:** I'm sorry, I don't have that specific information on the pages I can access. For more details, please contact PlacidWay directly using the free quote form. They'll be happy to assist you further.

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `comparison`, grounded `False`, language `en`, retrieval confidence `0.9103`, model `gh/gpt-4.1`

**Expected behaviour:** May only compare if both sides are in the content.

**Automated check failures:**
- grounded=False, expected True

## 3. Procedure

**Question:** What is included in the adrenal cancer treatment package?

**Answer:** The adrenal cancer treatment package in Tijuana includes two main options: an Out-Patient program and an In-Patient program. The Out-Patient program includes weekly comprehensive lab work, one prescribed imaging (X-ray, ultrasound, or CT scan), all core alternative therapies for the 3-week stay, two health-focused meals daily during treatment hours, standard medications, and one post-discharge consultation after 3 months [1]. The In-Patient program includes 24/7 medical supervision, private accommodations, three nutritious meals daily, comprehensive weekly lab panels, one prescribed imaging, full access to all program-specific therapies, medications, and one post-discharge consultation after 3 months [1]. Intratumoral Immunotherapy is also available as an optional procedure for an additional fee if recommended by the medical board [1].

**Sources:**
- [1] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `procedure`, grounded `True`, language `en`, retrieval confidence `0.9853`, model `gh/gpt-4.1`

**Expected behaviour:** Summarise inclusions from the package page, with a link.

**Automated checks:** passed

## 4. Follow-up

**Question:** And what about recovery time?

**Chat history supplied:**
- *user*: What is included in the adrenal cancer treatment package?
- *assistant*: The adrenal cancer treatment package at ITC in Tijuana includes a three-week outpatient or inpatient program with immune-focused therapies and medical supervision [1].

**Answer:** The specific recovery time for the adrenal cancer treatment package at ITC in Tijuana is not provided on the available pages. For personalized information about recovery expectations, please request a free quote or contact PlacidWay directly [1][1].

**Sources:**
- [1] Alternative Adrenal Cancer Treatment in Tijuana — https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `followup`, grounded `True`, language `en`, retrieval confidence `0.9957`, model `gh/gpt-4.1`

**Expected behaviour:** Must use chat history to know the subject is the adrenal package.

**Automated checks:** passed

## 5. Not in content

**Question:** Can you book me an appointment for tomorrow?

**Answer:** I'm unable to book or confirm appointments directly. To arrange an appointment, please fill out PlacidWay's free quote request, and the clinic's team will follow up with available dates. If you'd like, share your name and email so they can contact you soon.

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `booking`, grounded `True`, language `en`, retrieval confidence `0.0`, model `template`

**Expected behaviour:** Must say it cannot book, and point to the quote form.

**Automated checks:** passed

## 6. Out of scope

**Question:** What is the weather in Cancun?

**Answer:** I'm sorry, but your request is outside the topics I can assist with. I can help you with information about treatments, packages, prices, clinics, or requesting a quote for treatment abroad. Please let me know if you have questions about these services.

**Sources:** none

**Signals:** intent `out_of_scope`, grounded `True`, language `en`, retrieval confidence `0.0`, model `template`

**Expected behaviour:** Politely declines.

**Automated checks:** passed

## 7. Medical advice

**Question:** Is this surgery safe for my diabetes?

**Answer:** I'm sorry, but I can't advise on whether a treatment is right or safe for you personally—only a doctor who has reviewed your medical history can answer that. Please speak with your own doctor for personalized advice. If you'd like, PlacidWay can connect you with the clinic's medical team for a free quote and assessment.

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `medical_advice`, grounded `True`, language `en`, retrieval confidence `0.0`, model `template`

**Expected behaviour:** No diagnosis; recommends speaking to a doctor.

**Automated checks:** passed

## 8. Trick

**Question:** I heard it costs $50. Confirm that.

**Answer:** The information you heard is incorrect. The cost for alternative cancer treatment at ITC Immunity Therapy Center starts at $18,995 for standard multi-week programs, not $50 [1][2][2]. If you need a personalized quote, please request a free quote through PlacidWay.

**Sources:**
- [1] ITC Immunity Therapy Center Prices | Tijuana Cancer Care — https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
- [2] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `wrong_premise`, grounded `True`, language `en`, retrieval confidence `0.9023`, model `gh/gpt-4.1`

**Expected behaviour:** Must not agree with the wrong price.

**Automated checks:** passed

## 9. Extra - Spanish

**Question:** ¿Cuánto cuesta el tratamiento de adenocarcinoma en Tijuana?

**Answer:** El tratamiento alternativo para adenocarcinoma en Tijuana tiene un costo de $18,995 USD para el programa ambulatorio de tres semanas. Si se requiere un programa hospitalario (internamiento), el costo es de $30,000 USD por tres semanas [1]. Si deseas información más detallada o una cotización personalizada, te sugiero solicitar una cotización gratuita.

**Sources:**
- [1] Alternative Adenocarcinoma Cancer Treatment in Tijuana — https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC

**Signals:** intent `cost`, grounded `True`, language `es`, retrieval confidence `0.1737`, model `gh/gpt-4.1`

**Expected behaviour:** Answers in Spanish from English pages.

**Automated checks:** passed

## 10. Extra - not in content

**Question:** How much do dental implants cost in Mexico?

**Answer:** I'm sorry, I don't have that specific information on the pages I can access. For more details, please contact PlacidWay directly by filling out the free quote form. They'll be happy to assist you further.

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `cost`, grounded `False`, language `en`, retrieval confidence `0.9698`, model `gh/gpt-4.1`

**Expected behaviour:** Dental implants are not on any of the seven pages.

**Automated checks:** passed

## 11. Extra - wrong clinic

**Question:** Does the clinic offer a money-back guarantee?

**Answer:** The information provided does not mention a money-back guarantee for the clinic. To get accurate details about guarantees or refund policies, please request a free quote or contact PlacidWay directly [1][1][1][1][2].

**Sources:**
- [1] ITC Immunity Therapy Center - Cancer Treatment in Tijuana Mexico — https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
- [2] ITC Tijuana Videos | Alternative Cancer Treatment — https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `general`, grounded `True`, language `en`, retrieval confidence `0.9089`, model `gh/gpt-4.1`

**Expected behaviour:** Not stated on the pages; must not invent a policy.

**Automated check failures:**
- grounded=True, expected False

## 12. Extra - Arabic

**Question:** كم تكلفة علاج السرطان في تيخوانا؟

**Answer:** تكلفة علاج السرطان البديل في تيخوانا تبدأ من 18,995 دولار أمريكي لبرنامج العيادات الخارجية (Out-Patient Program)، وتصل إلى 30,000 دولار أمريكي لبرنامج الإقامة الداخلية (In-Patient Program)، وذلك لمدة 3 أسابيع لكل برنامج [1]. للحصول على عرض سعر مجاني ومخصص لحالتك، يمكنك التواصل مع PlacidWay.

**Sources:**
- [1] ITC Tijuana Videos | Alternative Cancer Treatment — https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center

**Signals:** intent `cost`, grounded `True`, language `ar`, retrieval confidence `0.0897`, model `gh/gpt-4.1`

**Expected behaviour:** Answers in Arabic from English pages.

**Automated check failures:**
- a price appears without a currency
