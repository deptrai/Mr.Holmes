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
    ) -> None:
        self.username = sanitize_username(username)
        self.mode = mode
        # Batch-mode config — skip interactive prompts when set
        self.batch_mode = batch_mode
        self._batch_proxy_choice = proxy_choice  # 1=proxy, 2=no proxy
        self._batch_nsfw = nsfw_enabled
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

    # ------------------------------------------------------------------
    # Stage 5: scan_sites() — Run scan against all sites
    # ------------------------------------------------------------------
    def scan_sites(self) -> None:
        """
        Call Controll() engine for main + optional NSFW site list.
        Populates self.successfull, self.successfullName, etc.
        """
        from Core.Searcher import MrHolmes  # local import to avoid circular

        nomefile = "Site_lists/Username/site_list.json"
        i1 = CO.Counter.Site(nomefile)
        MrHolmes.Controll(
            self.username, nomefile,
            self.cfg.proxy_identity or "None",
            self.ctx.report_path,
            self.ctx.subject_type,
            self.successfull, self.scraper_sites,
            True,                            # Writable
            self._http_proxy2,
            self.successfullName,
            self.cfg.proxy_dict,
            self._proxy_choice,
            self.tags, self.most_tags,
        )

        # In batch mode, use pre-configured flag; otherwise prompt
        if self.batch_mode:
            nsfw = 1 if self._batch_nsfw else 2
        else:
            nsfw = safe_int_input(
                Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
                Language.Translation.Translate_Language(
                    filename, "Username", "Default", "Nsfw") +
                Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
                valid_range=range(1, 3))

        if nsfw == 1:
            nsfw_file = "Site_lists/Username/NSFW_site_list.json"
            i2 = CO.Counter.Site(nsfw_file)
            MrHolmes.Controll(
                self.username, nsfw_file,
                self.cfg.proxy_identity or "None",
                self.ctx.report_path,
                self.ctx.subject_type,
                self.successfull, self.scraper_sites,
                True,
                self._http_proxy2,
                self.successfullName,
                self.cfg.proxy_dict,
                self._proxy_choice,
                self.tags, self.most_tags,
            )
            self.count = i1 + i2
        else:
            self.count = i1

    # ------------------------------------------------------------------
    # Stage 6: handle_results() — Print results + optional scraping
    # ------------------------------------------------------------------
    def handle_results(self) -> None:
        """Print found URLs and prompt user for profile scraping."""
        logger.info(Language.Translation.Translate_Language(
            filename, "Default", "TotFound", "None").format(
                self.ctx.subject_type, self.username))
        sleep(3)

        if not self.successfull:
            logger.warning(Language.Translation.Translate_Language(
                filename, "Username", "Default", "NoFound"
            ).format(self.username))
            return

        for url in self.successfull:
            logger.info("[FOUND] %s", url)
            self.found += 1

        if self.scraper_sites:
            self._dispatch_scrapers()
        else:
            logger.warning(Language.Translation.Translate_Language(
                filename, "Username", "Default", "NoScrape"))

    def _dispatch_scrapers(self) -> None:
        """Prompt user and dispatch available scrapers for found sites."""
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

        recap_choice = safe_int_input(
            Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
            Language.Translation.Translate_Language(
                filename, "Default", "Hypo", "None") +
            Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
            valid_range=range(1, 3))

        if recap_choice == 1:
            self._write_recap()

        self._prompt_dorks_and_transfer()

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

    def _prompt_dorks_and_transfer(self) -> None:
        """Prompt for dorks, notification, transfer, encoding."""
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

        Notification.Notifier.Start(self.mode)
        Creds.Sender.mail(final_report, self.username)

        transfer_choice = safe_int_input(
            Font.Color.BLUE + "\n[?]" + Font.Color.WHITE +
            Language.Translation.Translate_Language(
                filename, "Transfer", "Question", "None") +
            Font.Color.GREEN + "[#MR.HOLMES#]" + Font.Color.WHITE + "-->",
            valid_range=range(1, 3))

        if transfer_choice == 1:
            FileTransfer.Transfer.File(final_report, self.username, ".txt")

        Encoding.Encoder.Encode(final_report)
        logger.info("Report: %s", final_report)
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
    ) -> list:
        """
        Task 2+3+4+5 — Concurrent site scanning with bounded semaphore.

        Args:
            site_configs:      list[SiteConfig] — sites to scan.
            username:          target username.
            proxy:             optional proxy string "http://host:port".
            concurrency_limit: max concurrent connections (AC2+AC3).

        Returns:
            Ordered list[ScanResult] — exceptions filtered out (AC4+AC5).
            Order preserved because asyncio.gather() preserves task order.
        """
        from Core.models import ScanResult
        import aiohttp

        sem = asyncio.Semaphore(concurrency_limit)

        async with aiohttp.ClientSession() as session:
            # Task 2 — build task list
            tasks = [
                ScanPipeline._scan_with_semaphore(sem, session, site, username, proxy)
                for site in site_configs
            ]
            # AC4 — gather preserves order; return_exceptions=True → AC5
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Task 3 — filter exceptions, keep valid ScanResult objects
        valid_results = [
            r for r in raw_results
            if isinstance(r, ScanResult)
        ]
        return valid_results
