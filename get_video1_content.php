<?php
    // 1. Session and function setup (using same setup as index.php to access $video0Exists, $stopRecordingPressed, etc.)
    session_id("regattastart");
    session_start();
    include_once 'functions.php'; // or whatever setup is needed

    // 2. Re-read necessary variables (e.g., $video0Exists, $stopRecordingPressed, $formData, etc.)
    // This is necessary because this file is loaded independently.
    $video0Exists = file_exists("images/video0.mp4") && filesize("images/video0.mp4") > 0;
    $video1Exists = file_exists("images/video1.mp4") && filesize("images/video1.mp4") > 0;
    $stopRecordingPressed = $_SESSION['stopRecordingPressed'] ?? false;
    $formData = $_SESSION['form_data'] ?? [];
    $num_video = isset($_SESSION['form_data']['num_video']) ? $_SESSION['form_data']['num_video'] : 1;

    // 3. Output ONLY the HTML for the video panel (Regattastart9/10 logic)
    if ($video0Exists) {
        echo '<div class="w3-panel w3-pale-red" style="text-align:center; padding:20px;">';
        // Check for "complete" status
        $status_file = '/var/www/html/status.txt';
        $video1File = 'images/video1.mp4';
        $videoComplete = file_exists($status_file) && trim(file_get_contents($status_file)) === 'complete';

        // 3. Output ONLY the HTML for the video panel (Case: Video is Complete)
        if ($num_video == 1) {
            // --- Output the final completed video block (The AJAX target) ---
            if ($videoComplete && file_exists($video1File) && filesize($video1File) > 1000) {
                echo '<h3>Finish video (video1.mp4)</h3>';
                echo '<video id="video1" data-fps="25" width="640" height="480" controls>
                        <source src="' . $video1File . '" type="video/mp4">
                    </video>';
                echo '<div>
                        <button type="button" onclick="stepFrame(1, -1)">Previous Frame</button>
                        <button type="button" onclick="stepFrame(1, 1)">Next Frame</button>
                    </div>';
            } else {
                // Output the same 'failure' message as Case 5 in index.php
                echo '<p style="font-size:18px;color:#555;">No boats detected,
                Video not available or incomplete.</p>';
            }
        } 
    }
?>
