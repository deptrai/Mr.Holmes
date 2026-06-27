# OSINT Fraud Check

Check if a person/entity is potentially fraudulent. Combines multiple OSINT signals to produce a risk score.

## When to Use
- User says "is this person a scammer?"
- User says "check if [phone/email/username] is legit"
- User says "fraud check on [target]"
- User wants to verify someone before a transaction

## Prerequisites
- Mr.Holmes MCP server connected
- Tools: search_phone, search_email, check_breach, run_maigret, search_username, run_plugin

## Fraud Check Playbook

### Step 1: Phone Verification
- `search_phone(phone)` — carrier info
- `run_plugin("VnPhone", phone, "phone")` — Vietnamese carrier
- Red flags: VoIP numbers, recently assigned, multiple SIM swaps

### Step 2: Email Verification
- `validate_email(email)` — format check
- `search_email(email)` — registered services
- `check_breach(email)` — breach history
- Red flags: No registrations, many breaches, temporary email domains

### Step 3: Username Cross-Reference
- `run_maigret(username)` — 500+ sites
- Check: account age, consistency across platforms
- Red flags: New accounts only, no social media presence, inconsistent profiles

### Step 4: Domain Check (if applicable)
- `search_domain(domain)` — DNS, IP
- `whois_lookup(domain)` — registration date
- Red flags: Recently registered, privacy protection, suspicious TLD

### Step 5: Risk Scoring
Calculate risk score (0-100):
- Phone VoIP / foreign: +20
- Email no registrations: +15
- Email many breaches: +10
- Username no social media: +20
- Username only on gaming/anonymous platforms: +10
- Domain <30 days old: +25
- Domain privacy protected: +10
- No cross-platform consistency: +15
- Inconsistent profile photos: +10

Score interpretation:
- 0-30: LOW RISK — likely legitimate
- 31-60: MEDIUM RISK — exercise caution
- 61-100: HIGH RISK — likely fraudulent

## Output
Produce a risk assessment report in Vietnamese:
- Điểm rủi ro (Risk Score): X/100
- Mức độ (Level): LOW/MEDIUM/HIGH
- Tín hiệu đáng ngờ (Red Flags)
- Tín hiệu đáng tin (Green Flags)
- Khuyến nghị (Recommendation)
