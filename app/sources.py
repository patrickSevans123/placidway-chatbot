"""The seven pages the assessment allows us to use, and nothing else.

The list is deliberately hard-coded. The brief says "Do not crawl beyond them",
so there is no link-following anywhere in the crawler: it fetches exactly these
URLs and stops.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    slug: str
    url: str
    title: str
    page_type: str
    # Short description used in the prompt so the model knows what each page is for.
    summary: str


SOURCES: tuple[Source, ...] = (
    Source(
        slug="clinic-profile",
        url="https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
        title="ITC Immunity Therapy Center - Alternative Cancer Treatment in Tijuana",
        page_type="Clinic profile",
        summary="Who the clinic is, where it is, doctors, accreditations, facilities, contact details.",
    ),
    Source(
        slug="package-adenocarcinoma",
        url="https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
        title="Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC",
        page_type="Treatment package",
        summary="Adenocarcinoma package: price, what is included, duration, recovery, FAQs.",
    ),
    Source(
        slug="package-adrenal",
        url="https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
        title="Alternative Adrenal Cancer Treatment Package in Tijuana, Mexico by ITC",
        page_type="Treatment package",
        summary="Adrenal cancer package: price, what is included, duration, recovery, FAQs.",
    ),
    Source(
        slug="package-anal",
        url="https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
        title="Alternative Anal Cancer Treatment Package in Tijuana, Mexico by ITC",
        page_type="Treatment package",
        summary="Anal cancer package: price, what is included, duration, recovery, FAQs.",
    ),
    Source(
        slug="clinic-videos",
        url="https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
        title="ITC Tijuana Videos - Alternative Cancer Treatment",
        page_type="Clinic videos",
        summary="Patient testimonial videos and treatment explainer videos from the clinic.",
    ),
    Source(
        slug="price-list",
        url="https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
        title="ITC Immunity Therapy Center - Price List",
        page_type="Price list",
        summary="The clinic's structured price list: procedure, details, price in USD.",
    ),
    Source(
        slug="price-comparison",
        url="https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1",
        title="Alternative Medicine Cost Abroad - Compare Prices 2026",
        page_type="Price comparison",
        summary="Average and range of alternative medicine prices across clinics and countries.",
    ),
)

BY_SLUG = {s.slug: s for s in SOURCES}
BY_URL = {s.url: s for s in SOURCES}
