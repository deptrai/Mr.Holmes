<?php
/*
 * GUI/Database/Search.php
 *
 * Story 6.3 — AC4: Cross-case search endpoint
 * Accepts POST ?query=... and returns matching subjects + findings from SQLite.
 *
 * AC5: Falls back to flat-file directory listing when SQLite unavailable.
 *
 * Copyright 2021-2025 Mr.Holmes contributors
 * License: GNU General Public License v3.0
 */

require_once("../Actions/Language_Controller.php");
require_once("../Actions/Session_Checker.php");
require_once("../Actions/Theme_Controller.php");
require_once("../Actions/Sqlite_Helper.php");

$File_Name = "Search.css";
?>
<!DOCTYPE html>
<html>
<head>
    <title>Cross-Case Search — Mr.Holmes</title>
    <?php Total_Languages(); ?>
    <script src="../Script/Author.js"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=0.9">
    <meta name="theme-color" content="#000000">
    <link rel="icon" href="../Icon/Base/Logo.png">
    <?php Body_Theme($File_Name); ?>
</head>
<?php
    require_once("../Actions/Language_Controller.php");
    $Modality = "Search";
    Get_Language($Modality);
?>
<div class="Top-bar">
    <p>MR.HOLMES</p>
    <div class="Link">
        <a href="Username.php"></a>
        <a href="Websites.php"></a>
        <a href="Phone.php"></a>
        <a href="Ports.php"></a>
        <a href="Email.php"></a>
        <a href="New_User.php"></a>
        <a href="Schema.php"></a>
        <a href="People.php"></a>
        <a href="Map.php"></a>
        <a href="Search.php">Search</a>
    </div>
</div>

<div class="Upper-card">
    <center>
    <form action="" method="POST">
        <p id="Const">CROSS-CASE SEARCH</p>
        <input type="text" placeholder="Subject or site name..." id="SearchQuery" name="SearchQuery" autocomplete="off">
        <button width="fit-content" id="But" name="SearchButton">Search</button>
    </center>
</div>
</form>

<?php
if (isset($_POST["SearchButton"])) {
    $raw_query = trim($_POST["SearchQuery"] ?? "");

    if ($raw_query === "") {
        echo "<p id='error' align='center'>Please enter a search term.</p>";
    } else {
        // Sanitize for display only (not for SQL — prepared statements handle that)
        $display_query = htmlspecialchars($raw_query, ENT_QUOTES);

        // AC4: Cross-case search via SQLite
        if (SqliteHelper::isAvailable()) {
            // Search across investigations by subject
            $inv_results = SqliteHelper::searchInvestigations($raw_query);
            // Search across findings by site_name
            $finding_results = SqliteHelper::searchFindings($raw_query);

            $has_results = (!empty($inv_results) || !empty($finding_results));

            if (!$has_results) {
                echo "<p id='error' align='center'>No results found for \"$display_query\" in database.</p>";
            } else {
                // ---- Matching Investigations ----
                if (!empty($inv_results)) {
                    echo "<p id='Const2'>INVESTIGATIONS matching \"$display_query\":</p>";
                    echo "<div class='Wrapper2'><div class='Data2'>";
                    echo "<table style='width:100%;border-collapse:collapse'>";
                    echo "<tr><th>Subject</th><th>Type</th><th>Date</th><th>Found/Total</th></tr>";
                    foreach ($inv_results as $row) {
                        $subj    = htmlspecialchars($row['subject'] ?? '', ENT_QUOTES);
                        $type    = htmlspecialchars($row['subject_type'] ?? '');
                        $date    = htmlspecialchars($row['created_at'] ?? '');
                        $found   = (int) ($row['total_found'] ?? 0);
                        $total   = (int) ($row['total_sites'] ?? 0);
                        $inv_id  = (int) ($row['id'] ?? 0);
                        echo "<tr>";
                        echo "<td><a href='Username.php' onclick=\"document.getElementById('Searcher').value='$subj';return false;\">$subj</a></td>";
                        echo "<td>$type</td>";
                        echo "<td>$date</td>";
                        echo "<td>$found / $total</td>";
                        echo "</tr>";
                    }
                    echo "</table></div></div>";
                }

                // ---- Matching Findings (sites) ----
                if (!empty($finding_results)) {
                    echo "<p id='Const2'>SITES matching \"$display_query\" (across all investigations):</p>";
                    echo "<div class='Wrapper2'><div class='Data2'>";
                    echo "<table style='width:100%;border-collapse:collapse'>";
                    echo "<tr><th>Subject</th><th>Site</th><th>URL</th><th>Date</th></tr>";
                    foreach ($finding_results as $row) {
                        $subj    = htmlspecialchars($row['subject'] ?? '');
                        $site    = htmlspecialchars($row['site_name'] ?? '');
                        $raw_url = $row['url'] ?? '';
                        $url     = htmlspecialchars($raw_url, ENT_QUOTES);
                        $date    = htmlspecialchars($row['created_at'] ?? '');
                        echo "<tr>";
                        echo "<td>$subj</td>";
                        echo "<td>$site</td>";
                        echo "<td><a href='$url' target='blank'>$url</a></td>";
                        echo "<td>$date</td>";
                        echo "</tr>";
                    }
                    echo "</table></div></div>";
                }
            }

        } else {
            // AC5: Flat-file fallback — list matching username directories
            $reports_dir = "../Reports/Usernames/";
            echo "<p id='Const2'>SQLite unavailable — Scanning flat files for \"$display_query\":</p>";
            echo "<div class='Wrapper2'><div class='Data2'>";

            $matched = false;
            if (is_dir($reports_dir)) {
                $entries = scandir($reports_dir);
                foreach ($entries as $entry) {
                    if ($entry === '.' || $entry === '..') continue;
                    if (stripos($entry, $raw_query) !== false) {
                        $txt_file  = $reports_dir . $entry . "/" . $entry . ".txt";
                        $exists    = file_exists($txt_file) ? "✓ Report found" : "No report";
                        echo "<p>$entry — $exists</p>";
                        $matched = true;
                    }
                }
            }

            if (!$matched) {
                echo "<p id='error'>No matching subjects found.</p>";
            }
            echo "</div></div>";
        }
    }
}
?>
</div>
</body>
</html>
