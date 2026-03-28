"""
Core/engine/scan_pipeline.py

ScanPipeline class — tách God Method MrHolmes.search() (500 LOC) thành
các pipeline methods riêng biệt.

Story 1.3 — Split God Method, Epic 1.
Dependencies: Story 1.1 (ScanContext/ScanResult dataclasses)
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from time import sleep
from typing import TYPE_CHECKING

from Core.Support import Banner_Selector as banner
from Core.Support import Clear
from Core.Support import Creds
from Core.Support import DateFormat
from Core.Support import Encoding
from Core.Support import FileTransfer
from Core.Support import Font
from Core.Support import Language
from Core.Support import Logs
from Core.Support import Notification

from Core.Support import Recap

from Core.Support import Site_Counter as CO
from Core.config.logging_config import get_logger

logger = get_logger(__name__)

from Core.Support.Username import Scraper
from Core.models import ScanContext, ScanConfig
from Core.models.validators import sanitize_username, safe_int_input

if TYPE_CHECKING:
    from Core.cli.output import OutputHandler

filename = Language.Translation.Get_Language()

# ---------------------------------------------------------------------------
# Concurrency config (Task 5 — AC3: configurable via env var)
# ---------------------------------------------------------------------------
SEMAPHORE_LIMIT: int = int(os.environ.get("MR_HOLMES_CONCURRENCY", "20"))


from Core.scrapers.registry import ScraperRegistry
from Core.proxy.manager import ProxyManager

class ScanPipeline:
    """
    Orchestrates a full username OSINT scan session.

    Replaces the 500 LOC God Method MrHolmes.search() with
    discrete, testable pipeline stages.

    Usage:
        pipeline = ScanPipeline(username, mode)
        pipeline.run()
    """

    def __init__(
        self,
        username: str,
        mode: str,
        *,
        batch_mode: bool = False,
        proxy_choice: int | None = None,
        nsfw_enabled: bool = False,
        output_handler: "OutputHandler | None" = None,
    ) -> None:
        self.username = sanitize_username(username)
        self.mode = mode
        # Batch-mode config — skip interactive prompts when set
        self.batch_mode = batch_mode
        self._batch_proxy_choice = proxy_choice  # 1=proxy, 2=no proxy
        self._batch_nsfw = nsfw_enabled
        # Output abstraction (AC5) — default to ConsoleOutput
        if output_handler is None:
            from Core.cli.output import ConsoleOutput
            self.output: OutputHandler = ConsoleOutput()
        else:
            self.output = output_handler
        self.ctx: ScanContext | None = None
        self.cfg: ScanConfig | None = None
        self._opt: int = 1  # 1=research, 2=scraping — for recap branching
        self._proxy_manager: ProxyManager | None = None
        # Accumulated results (legacy lists — will be replaced by ScanResult in Story 2.x)
        self.successfull: list = []
        self.successfullName: list = []
        self.scraper_sites: list = []
        self.tags: list = []
        self.most_tags: list = []
        self.instagram_params: list = []
        self.twitter_params: list = []
        self.post_locations: list = []
        self.post_gps: list = []
        self.found: int = 0
        self.count: int = 0
        self.scrape_op: str = "Negative"
        # Story 6.2 — ReportWriter dual-write accumulator
        self.scan_results: list = []  # list of ScanResult

    # ------------------------------------------------------------------
    # Stage 1: setup() — Initialize context, paths, variables
    # ------------------------------------------------------------------
    def setup(self) -> ScanContext:
        """Initialize ScanContext with paths derived from username."""
        folder = "GUI/Reports/Usernames/{}/".format(self.username)
        self.ctx = ScanContext(
            target=self.username,
            subject_type="USERNAME",
            report_path=folder + self.username + ".txt",
            json_output_path="GUI/Reports/Usernames/{}/{}.json".format(
                self.username, self.username),
            json_names_path="GUI/Reports/Usernames/{}/{}.json".format(
                self.username, "Name"),
        )
        Clear.Screen.Clear()
        banner.Random.Get_Banner("Banners/Username", self.mode)
        logger.debug("INFO: %s", Language.Translation.Translate_Language(
            filename, "Username", "Default", "Explanation"))
        return self.ctx

    # ------------------------------------------------------------------
    # Stage 2: clean_old_reports() — Delete previous scan files
    # ------------------------------------------------------------------
    def clean_old_reports(self) -> None:
        """Clear previous scan output for this username."""
        folder = "GUI/Reports/Usernames/{}/".format(self.username)
        report = self.ctx.report_path
        report2 = folder + self.username + ".mh"
        recap1 = folder + "Recap.txt"
        recap2 = folder + "Recap.mh"

        def _clean_folder_files():
            for json_name in ["Name.json",
                              self.username + ".json"]:
                p = folder + json_name
                if os.path.exists(p):
                    os.remove(p)
            for recap in [recap1, recap2]:
                if os.path.exists(recap):
                    os.remove(recap)

        if os.path.exists(report):
            os.remove(report)
            _clean_folder_files()
            logger.debug(Language.Translation.Translate_Language(
                filename, "Default", "Delete", "None").format(self.username))
        elif os.path.exists(report2):
            os.remove(report2)
            _clean_folder_files()
            logger.debug(Language.Translation.Translate_Language(
                filename, "Default", "Delete", "None").format(self.username))
        else:
            os.mkdir(folder)

    # ------------------------------------------------------------------
    # Stage 3: configure_proxy() — User chooses proxy, resolve identity
    # ------------------------------------------------------------------
    def configure_proxy(self) -> ScanConfig:
        """Ask user for proxy preference and build ScanConfig via ProxyManager.

        In batch mode, uses self._batch_proxy_choice (default 2 = no proxy)
        to skip the interactive prompt.
        """
        if self.batch_mode and self._batch_proxy_choice is not None:
            choice = self._batch_proxy_choice
        else:
            choice = safe_int_input(
                Font.Color.BLUE + "\n[+]" + Font.Color.WHITE +
                Language.Translation.Translate_Language(
                    filename, "Default", "choice", "None") +
                Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
                valid_range=range(1, 3))

        self._proxy_manager = ProxyManager()
        self._proxy_manager.configure(choice)

        http_proxy = self._proxy_manager.get_proxy()
        identity   = self._proxy_manager.get_identity()

        # Legacy: keep raw IP string for display in scan_sites / _dispatch_scrapers
        self._proxy_choice = choice
        self._http_proxy2  = self._proxy_manager.proxy_ip

        self.cfg = ScanConfig(
            proxy_enabled=(choice == 1),
            proxy_dict=http_proxy,
            proxy_identity=identity,
        )
        return self.cfg

    # ------------------------------------------------------------------
    # Stage 4: prepare_report() — Write report headers, init log
    # ------------------------------------------------------------------
    def prepare_report(self) -> None:
        """Write date/header to report file and initialize log."""
        now = datetime.now()
        dt_string = now.strftime(DateFormat.Get.Format())
        date_str = "Date: " + str(dt_string)

        # Remove stale report if exists (secondary cleanup)
        if os.path.isfile(self.ctx.report_path):
            os.remove(self.ctx.report_path)
            logger.debug(Language.Translation.Translate_Language(
                filename, "Default", "Delete", "None").format(self.username))

        Logs.Log.Checker(self.username, "Username")

        with open(self.ctx.report_path, "a") as f:
            f.write(Language.Translation.Translate_Language(
                filename, "Report", "Default", "Date").format(date_str) + "\r\n")
            f.write(Language.Translation.Translate_Language(
                filename, "Report", "Username", "Found"))

    def _load_site_configs(self, json_file: str) -> list:
        """Parse site_list.json into typed SiteConfig objects."""
        import json
        from Core.engine.async_search import SiteConfig
        from Core.models import ErrorStrategy
        
        configs = []
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for item in data:
            for key, site_data in item.items():
                exceptions = site_data.get("exception", [])
                if any((char and char in self.username) for char in exceptions):
                    continue
                
                error_str = site_data.get("Error", "Status-Code")
                if error_str == "Message":
                    strategy = ErrorStrategy.MESSAGE
                elif error_str == "Response-Url":
                    strategy = ErrorStrategy.RESPONSE_URL
                else:
                    strategy = ErrorStrategy.STATUS_CODE
                
                url_template = site_data.get("user2", site_data.get("user", ""))
                # Handle edge cases where user2 is not a format string
                display_url = site_data.get("user", "").replace("{}", self.username)
                
                config = SiteConfig(
                    name=site_data.get("name", key),
                    url_template=url_template,
                    display_url=display_url,
                    error_strategy=strategy,
                    error_text=site_data.get("text", ""),
                    response_url=site_data.get("Response_url", ""),
                    tags=site_data.get("Tag", []),
                    is_scrapable=(site_data.get("Scrapable", "False") == "True")
                )
                configs.append(config)
        return configs

    # ------------------------------------------------------------------
    # Stage 5: scan_sites() — Run scan against all sites
    # ------------------------------------------------------------------
    def scan_sites(self) -> None:
        """
        Run the fully async concurrent OSINT scan using Epic 2 engine.
        Updates Rich Output live.
        """
        import asyncio
        from Core.models.scan_result import ScanStatus

        # 1. Parse configs
        main_configs = self._load_site_configs("Site_lists/Username/site_list.json")
        all_configs = main_configs

        # In batch mode, use pre-configured flag; otherwise prompt
        if self.batch_mode:
            nsfw = 1 if self._batch_nsfw else 2
        else:
            from Core.Support import Font, Language
            nsfw = safe_int_input(
                Font.Color.BLUE + "[+]" + Font.Color.WHITE +
                Language.Translation.Translate_Language(
                    filename, "Default", "NSFW", "None") +
                Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
                valid_range=range(1, 4))

        if nsfw == 1:
            nsfw_configs = self._load_site_configs("Site_lists/Username/site_list_NSFW.json")
            all_configs.extend(nsfw_configs)

        # 2. Setup Progress Tracker
        if hasattr(self.output, "begin_progress"):
            self.output.begin_progress(len(all_configs))

        # 3. Define live callback
        def _on_progress(res):
            self.count += 1
            if hasattr(self.output, "progress"):
                self.output.progress(self.count, len(all_configs))
            if res.status.value == "found":
                self.output.found(res.url, res.site_name)
                self.successfull.append(res.url)
                self.successfullName.append(res.site_name)
                # Save to text report file
                with open(self.ctx.report_path, "a", encoding="utf-8") as rf:
                    rf.write("[{}] {}\n".format(res.site_name, res.url))
                # Parse tags
                for tag in res.tags:
                    if tag not in self.tags:
                        self.tags.append(tag)
                    else:
                        if tag not in self.most_tags:
                            self.most_tags.append(tag)
                if res.is_scrapable:
                    self.scraper_sites.append(res.site_name)
            # Story 6.2: accumulate all results for ReportWriter
            self.scan_results.append(res)

        # 4. Trigger Async Scan
        actual_proxy = self._http_proxy2 if self._http_proxy2 and self._http_proxy2 != "None" else None
        
        asyncio.run(
            self.scan_all_sites(
                all_configs,
                self.username,
                actual_proxy,
                concurrency_limit=SEMAPHORE_LIMIT,
                on_progress=_on_progress
            )
        )

        if hasattr(self.output, "end_progress"):
            self.output.end_progress()

    # ------------------------------------------------------------------
    # Stage 6: handle_results() — Print results + optional scraping
    # ------------------------------------------------------------------
    def handle_results(self) -> None:
        """Print found URLs and prompt user for profile scraping."""
        logger.info(Language.Translation.Translate_Language(
            filename, "Default", "TotFound", "None").format(
                self.ctx.subject_type, self.username))
        if not self.batch_mode:
            sleep(3)

        if not self.successfull:
            logger.warning(Language.Translation.Translate_Language(
                filename, "Username", "Default", "NoFound"
            ).format(self.username))
            return

        for url in self.successfull:
            logger.info("[FOUND] %s", url)
        self.found = len(self.successfull)

        # Emit summary via OutputHandler (AC5)
        self.output.summary(self.found, self.count, self.username)

        # --- Story 6.2: DUAL-WRITE via ReportWriter (JSON + SQLite) ---
        try:
            from Core.reporting.writer import ReportWriter
            from Core.models.scan_context import ScanConfig as _ScanConfig
            writer = ReportWriter()
            writer.write_json_and_sqlite(
                ctx=self.ctx,
                cfg=self.cfg if self.cfg is not None else _ScanConfig(),
                results=self.scan_results,
                total_sites=self.count,
            )
        except Exception as exc:
            logger.warning("ReportWriter failed (scan unaffected): %s", exc)

        # --- EPIC 6: APIFY HYBRID INTEGRATION ---
        if "Instagram" in self.successfullName:
            from Core.engine.apify_scraper import ApifyScraper
            apify = ApifyScraper()
            if apify.is_enabled():
                logger.info("Apify API Token detected. Running Advanced Instagram Scraper...")
                try:
                    enriched = asyncio.run(apify.scrape_instagram_profile(self.username))
                except RuntimeError:
                    logger.warning("Cannot run Apify scraper: event loop conflict")
                    enriched = {}
                if enriched:
                    logger.info("Successfully fetched deep data from Instagram via Apify.")
                    with open(self.ctx.report_path, "a", encoding="utf-8") as rf:
                        rf.write("\n==========================================\n")
                        rf.write("[APIFY DEEP SCRAPE ENRICHMENT - INSTAGRAM]\n")
                        rf.write("Full Name: {}\n".format(enriched.get('full_name', '')))
                        rf.write("Bio: {}\n".format(enriched.get('bio', '')))
                        rf.write("Followers: {} | Following: {}\n".format(
                            enriched.get('followers', ''), enriched.get('following', '')))
                        rf.write("Posts: {}\n".format(enriched.get('posts', '')))
                        rf.write("Profile Picture URL: {}\n".format(enriched.get('profile_pic', '')))
                        rf.write("==========================================\n\n")

        if self.scraper_sites:
            self._dispatch_scrapers()
        else:
            logger.warning(Language.Translation.Translate_Language(
                filename, "Username", "Default", "NoScrape"))

    def _dispatch_scrapers(self) -> None:
        """Prompt user and dispatch available scrapers for found sites."""
        if self.batch_mode:
            self.scrape_op = "Negative"
            return
            
        # Ensure Profile_pics dir exists
        os.chdir("GUI/Reports/Usernames/{}".format(self.username))
        if not os.path.isdir("Profile_pics"):
            os.mkdir("Profile_pics")
        os.chdir("../../../../")

        choice = safe_int_input(
            Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
            Language.Translation.Translate_Language(
                filename, "Username", "Default", "Scraper") +
            Font.Color.GREEN + "[*MR.HOLMES*]" + Font.Color.WHITE + "-->",
            valid_range=range(1, 3))

        if choice != 1:
            self.scrape_op = "Negative"
            return

        self.scrape_op = "Positive"
        scrape_choice = safe_int_input(
            Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
            Language.Translation.Translate_Language(
                filename, "Default", "choice", "None") +
            Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
            valid_range=range(1, 3))

        if scrape_choice == 1:
            scrape_pm = ProxyManager()
            scrape_pm.configure(1)
            http_proxy = scrape_pm.get_proxy()
            http_proxy2 = scrape_pm.proxy_ip
            identity = scrape_pm.get_identity()
        else:
            http_proxy = None
            http_proxy2 = str(None)
            identity = None

        logger.info("Proxy: %s", http_proxy2)
        if identity:
            logger.info("Identity: %s", identity)

        self._run_scrapers(http_proxy)

    def _run_scrapers(self, http_proxy) -> None:
        """Dispatch available scrapers via ScraperRegistry."""
        registry = ScraperRegistry.build_username_registry(
            self.ctx.report_path, self.username,
            self.instagram_params, self.post_locations,
            self.post_gps, self.twitter_params,
        )
        registry.dispatch(self.scraper_sites, http_proxy)

    # ------------------------------------------------------------------
    # Stage 7: finalize() — Recap, hobbies, encoding, notification
    # ------------------------------------------------------------------
    def finalize(self) -> None:
        """Write recap, interests, encode report, send notification."""
        self._handle_gps_data()

        if self.batch_mode:
            self._write_recap()
            self._prompt_dorks_and_transfer(skip_prompts=True)
            return

        recap_choice = safe_int_input(
            Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
            Language.Translation.Translate_Language(
                filename, "Default", "Hypo", "None") +
            Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
            valid_range=range(1, 3))

        if recap_choice == 1:
            self._write_recap()

        self._prompt_dorks_and_transfer(skip_prompts=False)

    def _handle_gps_data(self) -> None:
        """Write GPS geolocation and visited places to report."""
        if not (self.post_gps or self.post_locations):
            return
        with open(self.ctx.report_path, "a") as f:
            logger.info("GETTING LATEST POST GEOLOCATION")
            f.write("\nGETTING LATEST POST GEOLOCATION:\n")
            for loc in self.post_gps:
                logger.info("[GPS] %s", loc)
                f.write(loc + "\n")
            logger.info("GETTING LATEST PLACE VISITED")
            f.write("\nGETTING LATEST PLACE VISITED:\n")
            for loc in self.post_locations:
                logger.info("[PLACE] %s", loc)
                f.write(loc + "\n")

    def _prompt_dorks_and_transfer(self, skip_prompts: bool = False) -> None:
        """Prompt for dorks, notification, transfer, encoding. Or execute silently if batch."""
        if skip_prompts:
            dork_choice = 2 # skip
        else:
            dork_choice = safe_int_input(
                Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
                Language.Translation.Translate_Language(
                    filename, "Default", "Dorks", "None") +
                Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
                valid_range=range(1, 3))

        from Core.Searcher import MrHolmes
        if dork_choice == 1:
            MrHolmes.Google_dork(self.username)
            MrHolmes.Yandex_dork(self.username)

        final_report = "GUI/Reports/Usernames/{}/{}.txt".format(
            self.username, self.username)
        print(Font.Color.WHITE +
              Language.Translation.Translate_Language(
                  filename, "Default", "Report", "None") + final_report)

        with open(final_report, "a") as f:
            f.write(Language.Translation.Translate_Language(
                filename, "Report", "Default", "By"))

        try:
            Notification.Notifier.Start(self.mode)
        except Exception as e:
            logger.warning("Notification failed: %s", e)
            
        try:
            Creds.Sender.mail(final_report, self.username)
        except Exception:
            pass

        if skip_prompts:
            transfer_choice = 2
        else:
            transfer_choice = safe_int_input(
                Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
                Language.Translation.Translate_Language(
                    filename, "Transfer", "Question", "None") +
                Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
                valid_range=range(1, 3))

        if transfer_choice == 1:
            FileTransfer.Transfer.File(final_report, self.username, ".txt")

        try:
            Encoding.Encoder.Encode(final_report)
        except Exception:
            pass
        
        logger.info("Report: %s", final_report)
        if not skip_prompts:
            input(Language.Translation.Translate_Language(
                filename, "Default", "Continue", "None"))

    def _write_recap(self) -> None:
        """Print and persist recap stats + possible hobbies/interests.

        Branching logic matches original:
          opt==1 (research)  → Recap.Stats.Printer()
          opt==2 (scraping)  → Hypothesis() for Instagram/Twitter
          Common             → Places, Hobbies, Encode
        """
        recap_file = "GUI/Reports/Usernames/{}/Recap.txt".format(self.username)

        if self._opt == 1:
            # Research mode — print stats summary
            if self.count > 0:
                percent = self.found / self.count * 100
                Recap.Stats.Printer(
                    self.username, self.found, self.count, percent,
                    self.ctx.subject_type, self.tags,
                    self.instagram_params, self.twitter_params,
                    self.scraper_sites, self.scrape_op, self.most_tags)
        else:
            # Scraping mode — hypothesis only
            if self.instagram_params:
                logger.info("INSTAGRAM HYPOTHESIS")
                Recap.Stats.Hypotesys(
                    self.instagram_params, self.username, recap_file)
            if self.twitter_params:
                logger.info("TWITTER HYPOTHESIS")
                Recap.Stats.Hypotesys(
                    self.twitter_params, self.username, recap_file)

        # Common: Places + Hobbies
        if self.post_locations:
            Recap.Stats.Places(
                self.post_locations, recap_file,
                self.instagram_params, self.username, self.most_tags)

        hobby_list = self.most_tags or self.tags or None
        if hobby_list:
            logger.info("GETTING POSSIBLE HOBBIES/INTERESTS")
            with open(recap_file, "a") as f:
                f.write("\nGETTING POSSIBLE HOBBIES/INTERESTS:\n")
                sleep(3)
                for hobby in hobby_list:
                    logger.info("[HOBBY] %s", hobby)
                    f.write(hobby + "\n")

        Encoding.Encoder.Encode(recap_file)

    # ------------------------------------------------------------------
    # Orchestrator: run() — Execute all pipeline stages in sequence
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Execute the full scan pipeline: setup → clean → proxy → scan → results → finalize."""
        self.setup()
        self.clean_old_reports()
        self.configure_proxy()
        self.prepare_report()

        # In batch mode, default to research (opt=1) — no interactive prompt
        if self.batch_mode:
            self._opt = 1
        else:
            self._opt = safe_int_input(
                Font.Color.BLUE + "\n[+]" + Font.Color.GREEN +
                "[INSERT AN OPTION]:" + Font.Color.WHITE +
                "\n(1)USERNAME-RESEARCH (SEARCH USERNAME ON DIFFERENT WEBSITES)"
                "\n(2)PROFILE-SCRAPING (SCRAPE USERNAME PROFILE DIRECTLY)" +
                Font.Color.GREEN + "\n\n[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
                valid_range=range(1, 3))

        if self._opt == 1:
            self.scan_sites()
            self.handle_results()
        else:
            # Direct scraping mode (opt == 2)
            from Core.Searcher import MrHolmes
            MrHolmes.Scraping(
                self.ctx.report_path, self.username,
                self.cfg.proxy_dict,
                self.instagram_params, self.post_locations,
                self.post_gps, self.twitter_params)

        self.finalize()

    # ------------------------------------------------------------------
    # Async concurrent scanning (Story 2.2 — Tasks 1-5)
    # ------------------------------------------------------------------
    @staticmethod
    async def _scan_with_semaphore(
        sem: asyncio.Semaphore,
        session,
        site_config,
        username: str,
        proxy: str | None,
    ):
        """
        Task 1 — Semaphore-bounded async request.

        `async with sem:` keeps concurrent connections ≤ SEMAPHORE_LIMIT.
        Yields control so other coroutines run while waiting.
        """
        from Core.engine.async_search import search_site  # local — avoid circular
        async with sem:
            return await search_site(session, site_config, username, proxy=proxy)

    @staticmethod
    async def scan_all_sites(
        site_configs: list,
        username: str,
        proxy: str | None = None,
        concurrency_limit: int = SEMAPHORE_LIMIT,
        on_progress = None,
    ) -> list:
        """
        Task 2+3+4+5 — Concurrent site scanning with bounded semaphore.

        Yields to on_progress callback as sites complete.
        Returns ordered list of ScanResults preserving submission order.
        """
        from Core.models import ScanResult
        import aiohttp

        sem = asyncio.Semaphore(concurrency_limit)

        async with aiohttp.ClientSession() as session:
            # Task 2 — build task list
            tasks = [
                asyncio.create_task(
                    ScanPipeline._scan_with_semaphore(sem, session, site, username, proxy)
                )
                for site in site_configs
            ]
            
            # Yield progress as they complete
            for f in asyncio.as_completed(tasks):
                try:
                    res = await f
                    if res is not None and on_progress:
                        on_progress(res)
                except Exception as e:
                    logger.debug("Task exception during scan: %s", e)

        # AC4 — Extract results in original order
        # F3: Guard against CancelledError when accessing task results
        valid_results = []
        for t in tasks:
            try:
                if not t.cancelled() and t.exception() is None:
                    res = t.result()
                    if res is not None:
                        valid_results.append(res)
            except (asyncio.CancelledError, asyncio.InvalidStateError):
                pass

        return valid_results
