# OSINT Due Diligence

Vet a business partner, company, or individual before entering a business relationship.

## When to Use
- User says "check this company"
- User says "due diligence on [business/person]"
- User says "vet this partner"
- User wants to verify business legitimacy

## Prerequisites
- Mr.Holmes MCP server connected
- Tools: search_domain, whois_lookup, run_plugin, search_person, generate_dorks

## Due Diligence Playbook

### Step 1: Business Registry Check
- `run_plugin("VnBusiness", tax_id_or_name, "tax_id")` — Vietnamese business registry
- Verify: registration status, legal representative, address, capital

### Step 2: Domain & Web Presence
- `search_domain(domain)` — DNS, IP
- `whois_lookup(domain)` — registration date, registrar
- Red flags: domain <90 days, privacy protection, offshore registrar

### Step 3: Legal Representative Profile
- `search_person(legal_rep_name)` — find online presence
- `run_maigret(legal_rep_username)` — social media
- Check: LinkedIn profile, professional history, consistency

### Step 4: Online Reputation
- `generate_dorks(company_name, "google")` — negative reviews, complaints
- `run_searxng(company_name + "scam|fraud|complaint|luật")` — reputation search
- Check: court records, news articles, review sites

### Step 5: Financial Signals
- `check_breach(known_emails)` — data breach exposure
- Cross-reference tax code with public databases

### Step 6: Report
Produce due diligence report in Vietnamese:
- Thông tin doanh nghiệp (Company Info)
- Lịch sử đăng ký (Registration History)
- Hồ sơ người đại diện (Legal Rep Profile)
- Danh tiếng trực tuyến (Online Reputation)
- Tín hiệu rủi ro (Risk Signals)
- Khuyến nghị (Recommendation: proceed/caution/decline)
