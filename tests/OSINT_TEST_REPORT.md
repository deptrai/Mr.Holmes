# OSINT Test Report — Real Data Verification

**Date:** 2026-06-26
**Environment:** macOS (Darwin), Python 3.10
**Project:** Mr.Holmes OSINT Tool
**Tester:** QA Engineer (automated subagent)
**Scope:** Legacy OSINT flows (email, phone, website) + modern plugin system (Epic 7-9)

---

## API Key Availability (.env)

Before running network-dependent tests, the `.env` file was inspected to
determine which API keys are configured:

| Key | Status |
|-----|--------|
| MH_SMTP_STATUS | SET |
| MH_SMTP_EMAIL | EMPTY |
| MH_SMTP_PASSWORD | EMPTY |
| MH_SMTP_DESTINATION | EMPTY |
| MH_SMTP_SERVER | SET |
| MH_SMTP_PORT | SET |
| MH_API_KEY | EMPTY |
| MH_CLI_PASSWORD | SET |
| MH_HAVEIBEENPWNED_API_KEY | EMPTY |
| MH_SHODAN_API_KEY | SET (len=32) |
| MH_LEAKLOOKUP_API_KEY | SET (len=32) |
| MH_SEARXNG_URL | EMPTY |
| MH_LLM_BASE_URL | SET |
| MH_LLM_API_KEY | SET |
| MH_LLM_MODEL | SET |
| MH_LLM_FALLBACK_BASE_URL | SET |
| MH_LLM_FALLBACK_API_KEY | SET |
| MH_LLM_FALLBACK_MODEL | SET |

> **Note:** `MH_HAVEIBEENPWNED_API_KEY` and `MH_SEARXNG_URL` are EMPTY, so
> the HaveIBeenPwned plugin cannot make authenticated calls and SearxNG
> falls back to DuckDuckGo HTML scraping.

---

## 1. Email Validation

**Source:** `Core/Support/Mail/Mail_Validator.py` (line 20)
**Regex:** `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
**Method:** `re.fullmatch()`

| Input | Expected | Actual | Status |
|-------|----------|--------|--------|
| test@gmail.com | VALID | VALID | ✅ PASS |
| user@domain.co.uk | VALID | VALID | ✅ PASS |
| invalid | INVALID | INVALID | ✅ PASS |
| @domain.com | INVALID | INVALID | ✅ PASS |
| user@.com | INVALID | INVALID | ✅ PASS |
| user@domain | INVALID | INVALID | ✅ PASS |
| a@b.io | VALID | VALID | ✅ PASS |

**Result:** ✅ PASS — All 7 test cases match expected behavior. The regex
correctly accepts standard emails with multi-level TLDs and rejects
malformed addresses.

---

## 2. Phone Number Country Mapping

**Source:** `Core/Support/Phone/Numbers.py` (lines 62-117)
**Logic:** Uses `phonenumbers` library to parse, detect country code,
country name, carrier, and timezone.

### Phone Lookup Files Available
`Site_lists/Phone/Lookup/` contains 7 country definition files:

| File | Country |
|------|---------|
| DEU_phone.json | Germany |
| FRA_phone.json | France |
| ITA_phone.json | Italy |
| ROU_phone.json | Romania |
| SWIS_phone.json | Switzerland |
| USA_phone.json | United States |
| Undefined.json | Fallback |

### Country Detection Results

| Input | Expected Nation | Actual Nation | Country | Valid | Status |
|-------|-----------------|---------------|---------|-------|--------|
| +1 6505551234 | US | US | United States | True | ✅ PASS |
| +39 3331234567 | IT | IT | (empty) | True | ✅ PASS |
| +44 7700900123 | GB | GB | (empty) | False | ✅ PASS |
| +49 15123456789 | DE | DE | Germany | True | ✅ PASS |
| +86 13800138000 | CN | CN | China | True | ✅ PASS |
| +999 12345 | ERROR | ERROR (invalid) | N/A | N/A | ✅ PASS |

**Result:** ✅ PASS — Country code detection works correctly for all valid
numbers. Invalid prefix `+999` raises a parse error as expected. Note:
`geocoder.country_name_for_number()` returns empty string for some
regions (IT, GB) — this is a known limitation of the phonenumbers
geocoder metadata, not a bug in Mr.Holmes.

---

## 3. Website/Domain OSINT — Traceroute

**Source:** `Core/Searcher_website.py` (lines 331-343)
**Logic:** `Web.trace()` selects `tracert` on Windows (`os.name == "nt"`)
and `traceroute` on Unix, then runs via `os.popen()`.

| Platform | Expected Command | Actual Command | Status |
|----------|------------------|----------------|--------|
| Darwin (macOS) | traceroute | traceroute | ✅ PASS |
| Windows (simulated) | tracert | tracert | ✅ PASS |

**Command generated:** `traceroute example.com` (on macOS)

**Result:** ✅ PASS — Platform detection correctly selects the appropriate
trace command. The logic uses `os.name == "nt"` for Windows detection,
which is the standard Python idiom.

---

## 4. Plugin System Discovery

**Source:** `Core/plugins/manager.py` — `PluginManager.discover_plugins()`
**Source:** `Core/config/settings.py` — `settings.get_plugin_key()`

| Plugin | Stage | Requires Key | API Key Status | Status |
|--------|-------|--------------|----------------|--------|
| DNSResolver | 1 | False | empty (N/A) | ✅ PASS |
| GitHub | 2 | False | empty (N/A) | ✅ PASS |
| HaveIBeenPwned | 1 | True | empty | ⚠️ KEY MISSING |
| Holehe | 2 | False | empty (N/A) | ✅ PASS |
| LeakLookup | 1 | True | set | ✅ PASS |
| Maigret | 2 | False | empty (N/A) | ✅ PASS |
| Numverify | 3 | True | empty | ⚠️ KEY MISSING |
| SearxngOSINT | 1 | False | empty (N/A) | ✅ PASS |
| Shodan | 1 | True | set | ✅ PASS |

**Total plugins discovered:** 9

**Result:** ✅ PASS — All 9 plugins discovered and instantiated correctly.
API keys are correctly loaded from `.env` for plugins that require them.
2 plugins (HaveIBeenPwned, Numverify) lack API keys and will not be able
to make authenticated calls.

---

## 5. DNS Resolver — Real Domains

**Source:** `Core/plugins/.../DNSResolver` plugin
**Method:** `await dns.check(domain, 'domain')`

| Domain | Expected | is_success | IPs Found | Status |
|--------|----------|------------|-----------|--------|
| github.com | resolves | True | 20.205.243.166 | ✅ PASS |
| google.com | resolves | True | 142.250.198.206 | ✅ PASS |
| cloudflare.com | resolves | True | 104.16.133.229, 104.16.132.229 | ✅ PASS |

**Result:** ✅ PASS — DNS resolution works correctly for all 3 real
domains. Returns valid IP addresses. Cloudflare correctly returns
multiple IPs (round-robin).

---

## 6. GitHub Plugin — Real Data

**Source:** `Core/plugins/.../GitHub` plugin
**Method:** `await gh.check(user, 'username')`

| Target | Expected | is_success | Real Name | Location | Status |
|--------|----------|------------|-----------|----------|--------|
| torvalds | found | True | Linus Torvalds | Portland, OR | ✅ PASS |
| gvanrossum | found | True | Guido van Rossum | San Francisco Bay Area | ✅ PASS |
| baduser12345notexist | not found | False | [] | N/A | ✅ PASS |

**Result:** ✅ PASS — GitHub plugin correctly fetches real profile data
for existing users and returns `is_success=False` for non-existent users.
Real names and locations are accurately retrieved from the GitHub API.

---

## 7. StagedProfiler — End-to-End

**Source:** `Core/engine/autonomous_agent.py` — `StagedProfiler`
**Input:** `torvalds` (username), `max_depth=1`
**Plugins:** All 9 discovered plugins (with available API keys)

| Metric | Value | Status |
|--------|-------|--------|
| Nodes | 98 | ✅ PASS |
| Edges | 97 | ✅ PASS |
| Plugin results | 13 | ✅ PASS |

### Sample Nodes (first 10)
| Target | Type | Depth |
|--------|------|-------|
| torvalds | username | 0 |
| Linus Torvalds | USERNAME | 1 |
| https://github.com/torvalds | PLATFORM | 1 |
| https://torvalds.wordpress.com/ | PLATFORM | 1 |
| https://bsky.app/profile/torvalds.bsky.social | PLATFORM | 1 |
| https://stackoverflow.com/users/filter?search=torvalds | PLATFORM | 1 |
| https://substack.com/@torvalds | PLATFORM | 1 |
| https://disqus.com/torvalds | PLATFORM | 1 |
| https://dribbble.com/torvalds | PLATFORM | 1 |
| https://discord.com | PLATFORM | 1 |

### Plugin Results Summary (first 5)
| Plugin | is_success | Status |
|--------|------------|--------|
| GitHub | True | ✅ PASS |
| Holehe | False | ⚠️ No email input |
| Maigret | True | ✅ PASS |
| DNSResolver | False | ⚠️ Not applicable for username |
| HaveIBeenPwned | False | ⚠️ No API key |

**Result:** ✅ PASS — StagedProfiler runs end-to-end successfully. It
builds a knowledge graph with 98 nodes and 97 edges from a single
username input. The profiler correctly invokes stage-appropriate plugins
and aggregates results. Some plugins return `is_success=False` due to
missing API keys or inapplicable target types (e.g., DNSResolver on a
username), which is expected behavior.

---

## 8. CLI Menu Navigation

**Source:** `MrHolmes.py` → `Core/Support/Menu.py`
**Test:** `echo "15" | python3.10 MrHolmes.py` (option 15 = EXIT)

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Banner displays | ASCII banner shown | ✅ Shown | ✅ PASS |
| Version shown | T.G.D-1.0.4 | T.G.D-1.0.4 | ✅ PASS |
| Menu options 1-15 | All 15 options listed | All 15 listed | ✅ PASS |
| Option 15 exits | Clean exit message | "THANK YOU FOR HAVE USED MR.HOLMES.. BYE:)" | ✅ PASS |
| Exit code | 0 | 0 | ✅ PASS |

**Result:** ✅ PASS — CLI starts correctly, displays the full menu with
all 15 options, and exits cleanly when option 15 (EXIT) is selected.

---

## 9. SearxNG / DuckDuckGo Fallback

**Source:** `Core/plugins/.../SearxngOSINT` plugin
**Input:** `torvalds` (username)
**Note:** `MH_SEARXNG_URL` is EMPTY, so the plugin falls back to
DuckDuckGo HTML scraping.

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| is_success | True | True | ✅ PASS |
| URLs found | > 0 | 10 | ✅ PASS |

### Sample URLs Found (first 5)
1. https://cisoseries.com/the-department-of-know-googles-codemender-cisas-big-leak-torvalds-open-source-warning/
2. https://www.bankinfosecurity.com/linux-crash-dump-flaws-expose-passwords-encryption-keys-a-28560
3. https://www.theregister.com/2019/01/08/linux_patch_page_cache/
4. https://haveibeenpwned.com/Passwords
5. https://www.exterro.com/resources/data-privacy-alerts/largest-password-dump-in-history-exposes-10-billion-credentials

**Result:** ✅ PASS — SearxNG plugin successfully falls back to DuckDuckGo
HTML scraping when no SearxNG URL is configured. Returns 10 relevant
OSINT URLs for the target username.

---

## Summary

| Test | Status |
|------|--------|
| 1. Email Validation | ✅ PASS (7/7) |
| 2. Phone Country Mapping | ✅ PASS (6/6) |
| 3. Website Traceroute | ✅ PASS (2/2) |
| 4. Plugin Discovery | ✅ PASS (9/9 plugins) |
| 5. DNS Resolver | ✅ PASS (3/3 domains) |
| 6. GitHub Plugin | ✅ PASS (3/3 users) |
| 7. StagedProfiler E2E | ✅ PASS (98 nodes, 97 edges) |
| 8. CLI Menu Navigation | ✅ PASS (clean start + exit) |
| 9. SearxNG/DuckDuckGo | ✅ PASS (10 URLs found) |

**Overall: 9/9 test groups PASSED**

---

## Issues Found

### Non-Blocking Issues (expected behavior / configuration gaps)

1. **HaveIBeenPwned API key missing** — `MH_HAVEIBEENPWNED_API_KEY` is
   EMPTY in `.env`. The plugin is discovered but cannot make authenticated
   API calls. StagedProfiler correctly reports `is_success=False` for this
   plugin. **Severity:** Low (configuration, not code bug).

2. **Numverify API key missing** — `MH_API_KEY` (used by Numverify) is
   EMPTY. Plugin discovered but cannot function. **Severity:** Low
   (configuration).

3. **SearxNG URL missing** — `MH_SEARXNG_URL` is EMPTY. The SearxngOSINT
   plugin falls back to DuckDuckGo HTML scraping, which works correctly.
   **Severity:** Info (fallback works as designed).

4. **Holehe plugin returns False for username input** — Holehe expects an
   email address, not a username. When run in StagedProfiler with a
   username target, it correctly returns `is_success=False`. This is
   expected behavior, not a bug. **Severity:** Info.

5. **DNSResolver returns False for username input** — DNSResolver expects
   a domain, not a username. When run in StagedProfiler with a username
   target, it correctly returns `is_success=False`. This is expected
   behavior. **Severity:** Info.

6. **phonenumbers geocoder returns empty country name for IT and GB** —
   `geocoder.country_name_for_number()` returns an empty string for
   Italian and UK numbers. This is a limitation of the `phonenumbers`
   library metadata, not a Mr.Holmes bug. The country code (IT, GB) is
   still correctly detected. **Severity:** Info (upstream library).

### No Code Bugs Found

All legacy OSINT flows (email validation, phone country mapping, website
traceroute) and modern plugin flows (DNS, GitHub, SearxNG, StagedProfiler)
function correctly. No code modifications were made during testing.

---

## Test Environment Notes

- **Python:** `python3.10` (as specified; `python3` has broken pyexpat)
- **Network:** Live internet connections used for DNS, GitHub API,
  DuckDuckGo, and StagedProfiler
- **Read-only:** No production code was modified
- **No commits:** Only this report file was created
