"""The companies tracked: 40 large US companies across sectors, chosen up front by size and
data quality, not by how they did. Two companies have short SEC histories because a corporate
reorganization gave them a new filer number (GOOGL from 2014, DIS from 2017). Banks and insurers are left out: their "revenue" is not
comparable (net interest income, premiums) and needs its own model (see docs/PRODUCT.md)."""

COMPANIES = {
    "tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "ORCL", "ADBE", "CRM", "CSCO", "INTC", "TXN", "QCOM"],
    "consumer": ["AMZN", "WMT", "COST", "HD", "MCD", "SBUX", "NKE", "KO", "PEP", "PG"],
    "health": ["JNJ", "PFE", "MRK", "ABBV", "LLY", "TMO"],
    "industrial": ["CAT", "DE", "HON", "UPS", "LMT"],
    "energy": ["COP", "CVX"],  # not XOM: its SEC company facts only start in 2025
    "communication": ["NFLX", "DIS", "VZ", "T", "CMCSA"],
}

TICKERS = [t for group in COMPANIES.values() for t in group]
SECTOR = {t: s for s, group in COMPANIES.items() for t in group}
