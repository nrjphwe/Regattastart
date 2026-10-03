<?php
    header("Access-Control-Allow-Origin: *");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: *");
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    define('APP_VERSION', '2025.12.29'); // You can replace '1.0.0' with your desired version number

    $custom_session_path = '/var/www/php_sessions';
    if (!file_exists($custom_session_path)) {
        mkdir($custom_session_path, 0777, true);
    }
    session_save_path($custom_session_path);

    // These must be set BEFORE session_start()
    ini_set('session.gc_maxlifetime', 86400);
    ini_set('session.cookie_lifetime', 86400);
    session_set_cookie_params(86400);

    // Use consistent session ID if sharing sessions across pages
    session_id("regattastart");
    session_start();

    // echo "The cached session pages expire after $cache_expire minutes";
    // echo "<br/>";
    ini_set('display_errors', 1);
    error_reporting(E_ALL);

    // Check if the session is already started
    // print_r($_SESSION);
    // echo "<br/>";
    // print_r($_POST);
    // echo "<br/>";
?>
<?php
    include_once 'functions.php';
    // Check if video0.mp4 or video1.mp4 exists and their sizes
    $video0Exists = file_exists("images/video0.mp4") && filesize("images/video0.mp4") > 0;
    $video1Exists = file_exists("images/video1.mp4") && filesize("images/video1.mp4") > 0;
    console_log("video0Exists = " . $video0Exists);
    console_log("video1Exists = " . $video1Exists);

    # initialize the status for Stop_recording button
    $stopRecordingPressed = $_SESSION['stopRecordingPressed'] ?? false;
    // Retrieve session data
    $formData = isset($_SESSION['form_data']) && is_array($_SESSION['form_data']) ? $_SESSION['form_data'] : [];

    $start_time = $formData['start_time'] ?? null;
    $num_starts = $formData['num_starts'] ?? null;
    // Extract relevant session data
    extract($formData); // This will create variables like $start_time, $video_end, etc.
    $start_mode = $formData['start_mode'] ?? 'standard';   // 'standard' | 'continuous'
    $continuous = ($start_mode === 'continuous');
    console_log("First start time: " . $start_time);


    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['stop_recording'])) 
    {
        // Handle stop recording logic here
        console_log('The stop_recording.php POST received in index.php');

        // Store this value in a session to persist it across requests
        $_SESSION['stopRecordingPressed'] = true;
        session_write_close(); // Close the session to allow other scripts to access it

        // Call the stop_recording.php logic directly
        //include 'stop_recording.php';
        exec("php /var/www/html/stop_recording.php > /dev/null 2>&1 &");

        $stopRecordingPressed = true;
        console_log('Stop recording started in the background');
    } else {
        console_log('Stop recording POST not received');
    }
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/w3.css">
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
    <!-- <meta http-equiv="refresh" content="200" -->
    <title>Regattastart</title>
    <link rel="icon" type="image/x-icon" href="/sailing-icon.jpeg">
    <!-- JavaScript to dynamically add a placeholder text or an image to the page when -->
    <!-- there are no pictures available yet. -->
     <script>const PLACEHOLDER_TEXT = <?php echo json_encode($continuous
        ? 'Pictures pending until first start'
        : 'Pictures pending until 5 minutes before start'); ?>;</script>
    <script> 
    // JavaScript function showPlaceholder
        function showPlaceholder() {
            var imageContainer = document.getElementById('image-container');
            var images = imageContainer.getElementsByTagName('img');
            var placeholderText = PLACEHOLDER_TEXT;
            // Check if there are images and if all images have loaded
            if (images.length > 0 && Array.from(images).every(img => img.complete)) {
                // Remove any existing placeholder text
                while (imageContainer.firstChild) {
                    imageContainer.removeChild(imageContainer.firstChild);
                }
            } else {
                // Add a placeholder text
                var textNode = document.createTextNode(placeholderText);
                imageContainer.appendChild(textNode);
            }
        }
    </script>
    <!-- set styles -->
    <style>
        img {
            max-width: 100%;
            height: auto;
        }
        video {
            max-width: 100%;
            height: auto;
        }
        .container {
            display: flex;
            flex-direction: column; /* Ensure items are stacked vertically */
            justify-content: center;
            align-items: center;
            height: 100vh; /* Optional: Makes the container full height */
        }
        .button-container {
            text-align: center;
        }
        .button-container button {
            display: inline-block;
            margin: 5px;
        }
    </style>
</head>
<body onload="showPlaceholder()">
    <!--Print session data on top of page -->
    <?php
        // Print data on top of page
        echo "<p style='font-size:12px'>";
        echo " Todays Date: " . date ("Y-m-d");
        echo ", Number of starts= $num_starts";
        echo ", First start at: " . $start_time;
        if (!empty($start_time) && strpos($start_time, ':') !== false) {
            list($start_hour, $start_minute) = explode(':', $start_time);
            $start_time_minutes = intval($start_hour) * 60 + intval($start_minute);
        } else {
            echo "<br><strong>Warning:</strong> Invalid or missing start time.";
            $start_time_minutes = 0; // Default or fallback value
        }

        if ($num_starts >= 2) {
            echo ", duration between starts: $dur_between_starts min";
            $ordinals = [2 => '2nd', 3 => '3rd'];
            for ($i = 2; $i <= $num_starts; $i++) {
                $t = $start_time_minutes + $dur_between_starts * ($i - 1);
                $label = $ordinals[$i] ?? "{$i}th";
                echo ", $label Start at: " . sprintf('%02d:%02d', floor($t / 60), $t % 60);
            }
        }

        if (isset($video_dur)) {
            echo "<br>";
            echo " Video duration: $video_dur min,"  ;
            echo " Video delay after start: $video_delay min,";
            echo " Number of videos during finish: " . $num_video;
        }
        if (isset($video_end)) {
            // Convert $start_time to minutes
            list($start_hour, $start_minute) = explode(':', $start_time);

            // Add video_end (duration after start) and additional 2 minutes
            $video_end_time_minutes = $start_time_minutes + $video_end + 2 + $dur_between_starts * ($num_starts - 1);

            // Convert video end time back to HH:MM format
            $video_end_hour = floor($video_end_time_minutes / 60);
            $video_end_minute = $video_end_time_minutes % 60;

            // Format video end time
            $video_end_time = sprintf('%02d:%02d', $video_end_hour, $video_end_minute);
            echo ", Video end time :  $video_end_time";
        }
        // Determine the number of videos during finish if not set, 
        // regattastart9 is executing and num_video is set to 1 as a flag.
        // This function checks if the variable $num_video is set
        $num_video = isset($num_video) ? $num_video : 1;
        console_log("num_video = $num_video"); // Log the value of $num_video
    ?>
    <!-- Header content -->
    <header>
        <!-- Title -->
        <div style="text-align: center;">
            <div class="w3-container w3-blue w3-text-white">
                <h1> Regattastart  </h1>
            </div>
        </div>
            <div style="text-align: center;">
                <?php
                    echo "     Version: " . APP_VERSION . "<br><p></p>"; 
                ?>
            </div>
            <div style="text-align: center;">
                <div id="image-container">
                    <!-- Your image elements will be added here dynamically -->
                </div>
            </div>
    </header>
    <!-- Here is our page's main content -->
    <main>
        <!-- Top button container -->
        <div class="button-container">
            <!-- Link to index8 -->
            <button class="w3-button w3-border w3-large w3-round-large w3-hover-grey w3-blue">
                <a href="/index8.php" title="Setup page Regattastart8" style="text-decoration: none; color: white;">
                    Regattastart8 - image detection Yolov8
                </a>
            </button>
        </div>
        <!-- Bilder tagna vid varje signal innan 1a start  -->
        <div style="text-align: center;" class="w3-panel w3-pale-blue">
            <h3><?php echo $continuous
                ? 'Bilder tagna vid varje start'
                : 'Bilder tagna vid varje signal innan 1a start'; ?></h3>
        </div>
        <!-- Refresh button -->
        <div style="text-align: center;" class="w3-panel w3-pale-grey">
            <button type="button" class="w3-button w3-round-large w3-khaki w3-hover-red" onclick="return refreshThePage()">Refresh page</button>
        </div> 

        <div style="text-align: center;">
        <?php
        if ($continuous) {
            for ($start_num = 1; $start_num <= $num_starts; $start_num++) {
                $filename  = "{$start_num}a_start_Start.jpg";
                $imagePath = 'images/' . $filename;
                if (file_exists($imagePath)) {
                    $imagePath .= '?' . filemtime($imagePath);
                    echo "<div><h3>Foto vid start $start_num</h3>";
                    echo "<img id='$filename' src='$imagePath' alt='$filename' width='640' height='480'></div>";
                } else {
                    console_log("picture Start $start_num do not exist");
                    break; // later starts cannot exist yet
                }
            }
        } else {
            // ---- original standard procedure, unchanged ----
            $prev_start_ok = true;
            for ($start_num = 1; $start_num <= $num_starts; $start_num++) {
                $prefix = "{$start_num}a_start";
                $labels = ['5_min' => '5 minuter', '4_min' => '4 minuter', '1_min' => '1 minut', 'Start' => null];
                if (!$prev_start_ok) break;
                echo "<div style='text-align: center;'>";
                $all_ok = true;
                foreach ($labels as $suffix => $label) {
                    $filename  = "{$prefix}_{$suffix}.jpg";
                    $imagePath = 'images/' . $filename;
                    if (file_exists($imagePath)) {
                        $imagePath .= '?' . filemtime($imagePath);
                        $heading = $label ? "Signal $label innan start $start_num" : "Foto vid start $start_num";
                        echo "<h3>$heading</h3>";
                        echo "<img id='$filename' src='$imagePath' alt='$filename' width='640' height='480'>";
                    } else {
                        console_log("picture $suffix start $start_num do not exist");
                        $all_ok = false;
                        break;
                    }
                }
                echo "</div>";
                $prev_start_ok = $all_ok;
            }
        }
        ?>
        </div>

            <!-- Display video0 when it is available -->
        <div style="text-align: center;" class="w3-panel w3-pale-blue">
            <?php
            // Which picture must exist before video0 is shown?
            if ($continuous || $num_starts == 2) {
                $trigger_pic = "images/{$num_starts}a_start_Start.jpg";   // last start
            } else {
                $trigger_pic = 'images/1a_start_Start.jpg';               // original behaviour
            }

            if (file_exists($trigger_pic)) {
                $video_name = 'images/video0.mp4';
                if (file_exists($video_name)) {
                    $txt = ($num_starts >= 2)
                        ? "Video från 5 min före start och 2 min efter sista start"
                        : "Video från 5 min före start och 2 min efter start";
                    echo "<h4> $txt</h4>";
                    echo '<video id="video0" width="640" height="480" controls><source src="' . $video_name . '" type="video/mp4"></video><p>';
                } else {
                    console_log("$video_name do not exists");
                }
            }
            ?>
        </div>
        <!-- Refresh button -->
        <div style="text-align: center;" class="w3-panel w3-pale-grey">
            <button type="button" class="w3-button w3-round-large w3-khaki w3-hover-red" onclick="return refreshThePage()">Refresh page</button>
        </div> 
        <!-- PHP Script to display video1 when available in w3-pale-red section -->
        <?php
            if ($video0Exists) {
                echo '<div class="w3-panel w3-pale-red" style="text-align:center; padding:20px;">';
                if ($num_video == 1) {
                    // --- Regattastart9/10 (only one video expected) ---
                    //$stopRecordingPressed = $_SESSION['stopRecordingPressed'] ?? false;
                    $status_file = '/var/www/html/status.txt';
                    $video1File = 'images/video1.mp4';
                    $videoComplete = file_exists('/var/www/html/status.txt') &&
                                    trim(file_get_contents('/var/www/html/status.txt')) === 'complete';

                    if (!$stopRecordingPressed)  {
                        // case 1: recording ongoing, stop recording not pressed and video not complete
                        if (!$videoComplete) {
                            echo '<form id="stopRecordingForm" method="post">
                                    <input type="hidden" name="stop_recording" value="true">
                                    <input type="hidden" id="stopRecordingPressed" name="stopRecordingPressed" value="0">
                                    <input type="submit" id="stopRecordingButton" value="Stop Recording">
                                </form>';
                            echo '<p style="font-size:18px;color:#555;">Recording in progress...</p>';
                        }
                        // Case 2: Recording completed by timeout (buttin not pressed)
                        if ($videoComplete && file_exists($video1File) && filesize($video1File) > 1000) {
                            // Case Video complete, show player
                            echo '<h3>Finish video (video1.mp4)</h3>';
                            // include a data-fps attribute so JS can use a sane frame time (adjust if you know FPS)
                            echo '<video id="video1" data-fps="25" width="640" height="480" controls>
                                    <source src="' . $video1File . '" type="video/mp4">
                                </video>';
                            // Buttons must be outside the <video> element
                            echo '<div>
                                    <button type="button" onclick="stepFrame(1, -1)">Previous Frame</button>
                                    <button type="button" onclick="stepFrame(1, 1)">Next Frame</button>
                                </div>';
                        }
                    } else {  // --- stopRecordingPressed) ---
                        if(!$videoComplete) {
                            // Case 3: Stop pressed, waiting for processing
                            echo '<div id="videoStatusDiv">
                                <p id="statusText" style="font-size:18px;color:#555;">Video being created...</p>
                            </div>';
                        } elseif (file_exists($video1File) && filesize($video1File) > 1000) {
                            // Case 4: Stop pressed, video complete, show player
                            echo '<h3>Finish video (video1.mp4)</h3>';
                            echo '<video id="video1" data-fps="25" width="640" height="480" controls>
                                    <source src="' . $video1File . '" type="video/mp4">
                                </video>';
                            echo '<div>
                                    <button type="button" onclick="stepFrame(1, -1)">Previous Frame</button>
                                    <button type="button" onclick="stepFrame(1, 1)">Next Frame</button>
                                </div>';
                        } else {
                            // Case 5: Stop pressed, but no boats detected video1.mp4 missing or incomplete
                            echo '<p style="font-size:18px;color:#555;">No boats detected,
                            Video not available or incomplete.</p>'; 
                        }
                    }
                } else {
                    // --- Regattastart6 (multiple videos) ---
                    for ($x = 1; $x <= $num_video; $x++) {
                        $video_name = "images/video$x.mp4";
                        if (file_exists($video_name) && filesize($video_name) > 1000) {
                            echo "<h3>Finish video (video{$x}.mp4)</h3>";
                            echo '<video id="video' . $x . '" data-fps="25" width="640" height="480" controls>
                                    <source src="' . $video_name . '" type="video/mp4">
                                </video>';
                            echo '<div>
                                    <button type="button" onclick="stepFrame(' . $x . ', -1)">Previous Frame</button>
                                    <button type="button" onclick="stepFrame(' . $x . ', 1)">Next Frame</button>
                                </div>';
                        } else {
                            echo "<p style='font-size:18px;color:#555;'>Video $x not available or incomplete.</p>";
                        }
                    }
                }
                echo '</div>'; // close pale-red panel always here
            }
        ?>
    </main>
    <!-- footer -->
    <div style="text-align: center;" class="w3-panel w3-grey">
        <?php
            // output index.php was last modified.
            $filename = 'index.php';
            if (file_exists($filename)) {
                echo "This web-page was last modified: \n" . date ("Y-m-d H:i:s.", filemtime($filename));
            } else {
                console_log("$filename do not exists");
            }
        ?>
    </div>
    <div style="text-align: center;" class="w3-panel w3-grey">
        <?php
            echo " Time now: " .date("H:i:s");
        ?> 
    </div>
    <!--- JavaScript poll video1, refresh, reload and step ) -->
    <script>
        const video1Exists = <?php echo json_encode($video1Exists); ?>;
        // --- Helper: scroll to bottom after reload ---
        window.addEventListener("load", () => {
            if (sessionStorage.getItem("scrollToBottom") === "true") {
                sessionStorage.removeItem("scrollToBottom");
                window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
            }
        });

        // --- Step-frame function (used by video controls) ---
        function stepFrame(videoNum, step) {
            const video = document.getElementById("video" + videoNum);
            if (!video) return;
            video.pause();
            const fps = parseFloat(video.getAttribute("data-fps")) || 25;
            const frameTime = 1 / fps;
            video.currentTime = Math.max(0, Math.min(video.duration || Infinity, video.currentTime + step * frameTime));
        }

        // --- Refresh button ---
        function refreshThePage() {
            // This command immediately reloads the entire page from the server.
            // Use true to force a full reload, ignoring the browser's cache.
            window.location.reload(true); 
            // You no longer need the setTimeout line.
        }

        // New interval: 3 to 5 seconds
        const RETRY_INTERVAL_MS = 3000; 

        // --- Poll for video1 completion ---
        function checkVideoCompletion() {
            //fetch("/status.txt?rand=" + Math.random(), { cache: "no-store" })
            fetch("/check_video_completion.php?rand=" + Math.random(), { cache: "no-store" })
                .then(r => r.text())
                .then(text => {
                    const status = text.trim();
                    if (status === "complete") {
                        console.log("✅ Video complete — reloading page now!");
                        // 💡 NEW AJAX CALL: Use jQuery to fetch the video player content
                        $("#video1-placeholder").load("/get_video1_content.php", function(response, status, xhr) {
                            if (status == "success") {
                                console.log("Video content successfully loaded. Polling finished.");
                                // Optional: Scroll to the new video player for user convenience
                                window.scrollTo({ top: $("#video1-placeholder").offset().top, behavior: "smooth" });
                                // 🛑 Polling successfully stopped.
                            } else {
                                console.error("Failed to load video content:", xhr.statusText);
                                // Fallback: If AJAX fails, resort to a full reload
                                setTimeout(() => window.location.reload(true), 5000); 
                            }
                        });

                        // CRUCIAL: Return here to stop the recursive setTimeout loop from running again.
                        return; 

                    } else {
                        console.log("⏳ Not ready yet, retrying in " + (RETRY_INTERVAL_MS / 1000) + "s...");
                        // Use the faster retry interval
                        setTimeout(checkVideoCompletion, RETRY_INTERVAL_MS); 
                    }
                })
                .catch(err => {
                    // Keep the error delay long, as errors suggest a server issue.
                    console.error("Error checking video completion:", err);
                    setTimeout(checkVideoCompletion, 60000);
                });
        }

        // --- Start polling automatically if video1 doesn’t exist ---
        if (!video1Exists) {
            console.log("Video1 not found — starting polling loop");
            setTimeout(checkVideoCompletion, 2000);
        } 
        // --- NEW LOGIC: If the video already exists, load the content immediately ---
        else { 
            console.log("Video1 file exists. Loading content directly.");
            // Force the AJAX load to get the video player HTML from the dedicated file
            $("#video1-placeholder").load("/get_video1_content.php", function(response, status, xhr) {
                if (status == "success") {
                    console.log("Initial load successful.");
                    window.scrollTo({ top: $("#video1-placeholder").offset().top, behavior: "smooth" });
                } else {
                    console.error("Failed to load existing video content:", xhr.statusText);
                }
            });
        }

        // --- Optional: handle manual stop button (if present) ---
        const stopButton = document.getElementById("stopRecordingButton");
        const stopInput = document.getElementById("stopRecordingPressed");
        if (stopButton && stopInput) {
            stopButton.addEventListener("click", e => {
                e.preventDefault();
                stopInput.value = "1";
                console.log("🛑 Stop Recording pressed — starting status polling");
                stopButton.closest("form").submit();
                setTimeout(checkVideoCompletion, 20000);
            });
        }
    </script>
</body>
</html>