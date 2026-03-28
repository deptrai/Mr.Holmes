<?php
/*
 * GUI/Actions/Sqlite_Helper.php
 *
 * Story 6.3 — PHP GUI SQLite Migration
 * Central helper for reading SQLite data in the GUI.
 *
 * AC1: PHP controllers can query SQLite
 * AC5: Falls back gracefully when SQLite unavailable
 *
 * Copyright 2021-2025 Mr.Holmes contributors
 * License: GNU General Public License v3.0
 */

class SqliteHelper {

    /** Absolute path to mrholmes.db (relative to this file location) */
    private static string $DB_PATH = __DIR__ . '/../../GUI/Reports/mrholmes.db';

    /** @var SQLite3|null — null when unavailable */
    private static ?SQLite3 $db = null;

    /** @var bool — set once on first check */
    private static bool $available_checked = false;
    private static bool $is_available = false;

    // ------------------------------------------------------------------
    // Task 1 — SQLite extension verification (AC5)
    // ------------------------------------------------------------------

    /**
     * Returns true if SQLite3 extension is loaded AND the DB file exists.
     */
    public static function isAvailable(): bool {
        if (self::$available_checked) {
            return self::$is_available;
        }
        self::$available_checked = true;
        self::$is_available = extension_loaded('sqlite3') && file_exists(self::$DB_PATH);
        return self::$is_available;
    }

    /**
     * Returns an open SQLite3 connection, or null if unavailable.
     * AC5: never throws — returns null on any error.
     */
    public static function getConnection(): ?SQLite3 {
        if (!self::isAvailable()) {
            return null;
        }
        if (self::$db !== null) {
            return self::$db;
        }
        try {
            self::$db = new SQLite3(self::$DB_PATH, SQLITE3_OPEN_READONLY);
            self::$db->busyTimeout(2000);
            return self::$db;
        } catch (Exception $e) {
            error_log('[SqliteHelper] Failed to open DB: ' . $e->getMessage());
            return null;
        }
    }

    // ------------------------------------------------------------------
    // Task 2 — Query helpers (AC1)
    // ------------------------------------------------------------------

    /**
     * Execute a SELECT query and return all rows as associative arrays.
     *
     * @param string $sql     SQL with ? placeholders
     * @param array  $params  Positional parameters
     * @return array|null     Rows array on success, null if DB unavailable or error
     */
    public static function query(string $sql, array $params = []): ?array {
        $db = self::getConnection();
        if ($db === null) {
            return null;
        }
        try {
            $stmt = $db->prepare($sql);
            if ($stmt === false) {
                error_log('[SqliteHelper] Prepare failed: ' . $db->lastErrorMsg());
                return null;
            }
            foreach ($params as $i => $val) {
                $stmt->bindValue($i + 1, $val);
            }
            $result = $stmt->execute();
            if ($result === false) {
                return null;
            }
            $rows = [];
            while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
                $rows[] = $row;
            }
            $result->finalize();
            $stmt->close();
            return $rows;
        } catch (Exception $e) {
            error_log('[SqliteHelper] Query error: ' . $e->getMessage());
            return null;
        }
    }

    /**
     * Execute a SELECT and return only the first row, or null.
     */
    public static function queryOne(string $sql, array $params = []): ?array {
        $rows = self::query($sql, $params);
        if ($rows === null || count($rows) === 0) {
            return null;
        }
        return $rows[0];
    }

    // ------------------------------------------------------------------
    // Task 3 — Investigation list query (AC2)
    // ------------------------------------------------------------------

    /**
     * Return all investigations for a given subject (username / phone / etc.)
     * ordered newest-first.
     *
     * @param string $subject The target (e.g. "luisphan")
     * @return array|null
     */
    public static function getInvestigations(string $subject): ?array {
        return self::query(
            'SELECT id, subject, subject_type, created_at, proxy_used, total_sites, total_found
             FROM investigations
             WHERE subject = ?
             ORDER BY created_at DESC',
            [$subject]
        );
    }

    /**
     * Return ALL investigations (for overview page), newest first.
     */
    public static function getAllInvestigations(): ?array {
        return self::query(
            'SELECT id, subject, subject_type, created_at, total_sites, total_found
             FROM investigations
             ORDER BY created_at DESC'
        );
    }

    // ------------------------------------------------------------------
    // Task 4 — Findings detail query (AC3)
    // ------------------------------------------------------------------

    /**
     * Return findings for a given investigation_id.
     * Optional $status_filter: 'found' | 'not_found' | null (all)
     *
     * @param int         $investigation_id
     * @param string|null $status_filter
     * @return array|null
     */
    public static function getFindings(int $investigation_id, ?string $status_filter = null): ?array {
        if ($status_filter !== null) {
            return self::query(
                'SELECT id, site_name, url, status, is_scrapable, scraped, error_type, created_at
                 FROM findings
                 WHERE investigation_id = ? AND status = ?
                 ORDER BY site_name',
                [$investigation_id, $status_filter]
            );
        }
        return self::query(
            'SELECT id, site_name, url, status, is_scrapable, scraped, error_type, created_at
             FROM findings
             WHERE investigation_id = ?
             ORDER BY site_name',
            [$investigation_id]
        );
    }

    /**
     * Return tags for a given finding.
     *
     * @param int $finding_id
     * @return array|null  e.g. [['id'=>1, 'name'=>'Social'], ...]
     */
    public static function getFindingTags(int $finding_id): ?array {
        return self::query(
            'SELECT t.id, t.name
             FROM tags t
             JOIN finding_tags ft ON ft.tag_id = t.id
             WHERE ft.finding_id = ?
             ORDER BY t.name',
            [$finding_id]
        );
    }

    // ------------------------------------------------------------------
    // Task 5 — Cross-case search (AC4)
    // ------------------------------------------------------------------

    /**
     * Search findings by site_name fragment across ALL investigations.
     * Useful for "was this site ever found for any target?"
     *
     * @param string $site_name_fragment  Partial name to match (LIKE %...%)
     * @return array|null  Each row includes investigation subject for context
     */
    public static function searchFindings(string $site_name_fragment): ?array {
        return self::query(
            'SELECT f.id, f.site_name, f.url, f.status, f.created_at,
                    i.subject, i.subject_type, i.id AS investigation_id
             FROM findings f
             JOIN investigations i ON i.id = f.investigation_id
             WHERE f.site_name LIKE ? AND f.status = \'found\'
             ORDER BY i.created_at DESC',
            ['%' . $site_name_fragment . '%']
        );
    }

    /**
     * Search investigations by subject fragment across ALL investigations.
     *
     * @param string $query  Partial subject to match
     * @return array|null
     */
    public static function searchInvestigations(string $query): ?array {
        return self::query(
            'SELECT id, subject, subject_type, created_at, total_sites, total_found
             FROM investigations
             WHERE subject LIKE ?
             ORDER BY created_at DESC',
            ['%' . $query . '%']
        );
    }
}
