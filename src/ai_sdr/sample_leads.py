from .schemas import RawLead

SAMPLE_RAW_LEADS = [
    RawLead(
        full_name="Laura Schmidt",
        title="Head of Marketing",
        company="Northwind SaaS",
        location="Berlin, Germany",
        email="laura@northwind.example",
        linkedin_url="https://linkedin.com/in/laura-schmidt",
        company_website="https://northwind.example",
        industry="SaaS",
        source="sample",
    ),
    RawLead(
        full_name="James Carter",
        title="Founder & CEO",
        company="Flowmetrics",
        location="London, United Kingdom",
        email="james@flowmetrics.example",
        linkedin_url="https://linkedin.com/in/james-carter",
        company_website="https://flowmetrics.example",
        industry="AI",
        source="sample",
    ),
    RawLead(
        full_name="Sofia Virtanen",
        title="VP of Growth",
        company="Helsinki Analytics",
        location="Helsinki, Finland",
        email="",
        linkedin_url="https://linkedin.com/in/sofia-virtanen",
        company_website="https://helsinkianalytics.example",
        industry="Software",
        source="sample",
    ),
    RawLead(
        full_name="Daniel Osei",
        title="Demand Generation Manager",
        company="BrightCloud",
        location="Remote, Europe",
        email="daniel@brightcloud.example",
        linkedin_url="https://linkedin.com/in/daniel-osei",
        company_website="https://brightcloud.example",
        industry="Technology",
        source="sample",
    ),
    RawLead(
        full_name="Priya Nair",
        title="Office Administrator",
        company="Local Dental Clinic",
        location="Manchester, United Kingdom",
        email="priya@dentalclinic.example",
        linkedin_url="",
        company_website="https://dentalclinic.example",
        industry="Healthcare",
        source="sample",
    ),
]


def get_sample_leads() -> list[RawLead]:
    return list(SAMPLE_RAW_LEADS)
