<?php
    header("Access-Control-Allow-Origin: *");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: *");
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    define('APP_VERSION', '2025.09.16'); // You can replace '1.0.0' with your desired version number

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
    $stopRecordingPressed = false;
    // Retrieve session data
    $formData = isset($_SESSION['form_data']) && is_array($_SESSION['form_data']) ? $_SESSION['form_data'] : [];
    $start_time = $formData['start_time'] ?? null;
    $num_starts = $formData['num_starts'] ?? null;
    // Extract relevant session data
    extract($formData); // This will create variables like $start_time, $video_end, etc.
    console_log("First start time: " . $start_time);

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['stop_recording'])) 
    {
        // Handle stop recording logic here
        console_log('The stop_recording.php POST received in index.php');
        $stopRecordingPressed = true;
        // Store this value in a session to persist it across requests
        $_SESSION['stopRecordingPressed'] = $stopRecordingPressed;

        // Call the stop_recording.php logic directly
        include 'stop_recording.php';

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
    <script> // JavaScript function showPlaceholder 
        function showPlaceholder() {
            var imageContainer = document.getElementById('image-container');
            var images = imageContainer.getElementsByTagName('img');
            var placeholderText = 'Pictures pending until 5 minutes before start';
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
    <?php
    // Print session data on top of page
        echo "<p style='font-size:12px'>";
        echo " First start at: " . $start_time;
        echo ", Number of starts= $num_starts";
        if (!empty($start_time) && strpos($start_time, ':') !== false) {
            list($start_hour, $start_minute) = explode(':', $start_time);
            $start_time_minutes = intval($start_hour) * 60 + intval($start_minute);
        } else {
            echo "<br><strong>Warning:</strong> Invalid or missing start time.";
            $start_time_minutes = 0; // Default or fallback value
        }

        if ($num_starts >= 2) {
            echo ", Duration between starts: $dur_between_starts min";
            // Calculate second start time in minutes
            $second_start_time_minutes = $start_time_minutes + $dur_between_starts * 1;
            // Convert second start time back to hours and minutes
            $second_start_hour = floor($second_start_time_minutes / 60);
            $second_start_minute = $second_start_time_minutes % 60;
            $second_start_time = sprintf('%02d:%02d', $second_start_hour, $second_start_minute);
            echo ", 2nd Start at: $second_start_time";
        }
        if ($num_starts == 3) {
             // Calculate third start time in minutes
            $third_start_time_minutes = $start_time_minutes + $dur_between_starts * 2;
            // Convert third start time back to hours and minutes
            $third_start_hour = floor($third_start_time_minutes / 60);
            $third_start_minute = $third_start_time_minutes % 60;
            // Format third start time
            $third_start_time = sprintf('%02d:%02d', $third_start_hour, $third_start_minute);
            echo ", 3rd Start at: $third_start_time";
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
        <!-- Button Container -->
        <div class="button-container">
            <!-- Link to index6 -->
            <button class="w3-button w3-border w3-large w3-round-large w3-hover-grey w3-blue">
                <a href="/index6.php" title="Setup page Regattastart6" style="text-decoration: none; color: white;">
                    Regattastart6 with 1 or 2 starts
                </a>
            </button>
            <!-- Link to index9 -->
            <button class="w3-button w3-border w3-large w3-round-large w3-hover-grey w3-green">
                <a href="/index9.php" title="Setup page Regattastart9" style="text-decoration: none; color: white;">
                    Regattastart9 -- with image detection
                </a>
            </button>
             <!-- Link to index10 -->
            <button class="w3-button w3-border w3-small w3-round-large w3-hover-grey w3-red">
                <a href="/index10.php" title="Setup page Regattastart10 " style="text-decoration: none; color: white;">
                    Regattastart10 with image & number detection
                </a>
            </button>
        </div>
        <!-- header text -->
        <div style="text-align: center;" class="w3-panel w3-pale-blue">
            <h3> Bilder tagna vid varje signal innan 1a start </h3>
        </div>
        <div style="text-align: center;" class="w3-panel w3-pale-grey">
            <button type="button" class="w3-button w3-round-large w3-khaki w3-hover-red" onclick="return refreshThePage()">Refresh page</button>
        </div> 
        <!-- Display pictures for the 1st start  -->
        <div style="text-align: center;">
            <?php
                // Check and display the first image
                $filename = '1a_start_5_min.jpg';
                $imagePath = 'images/' . $filename; // Relative path
                if (file_exists($imagePath)) 
                {
                    $imagePath .= '?' . filemtime($imagePath);
                    echo "<h3> Varningssignal 5 minuter innan 1a start</h3>";
                    echo "<img id='$filename' src='$imagePath' alt='1a_start 5 min picture' width='640' height='406' loading='lazy' />";

                    // Check and display the second image
                    $filename = '1a_start_4_min.jpg';
                    $imagePath = 'images/' . $filename; // Relative path
                    if (file_exists($imagePath)) 
                    {
                        $imagePath .= '?' . filemtime($imagePath);
                        echo "<h3> Signal 4 minuter innan 1a start </h3>";
                        echo "<img id='$filename' src='$imagePath' alt='1a_start 4 min picture' width='640' height='480'>";

                        // Check and display the third image
                        $filename = '1a_start_1_min.jpg';
                        $imagePath = 'images/' . $filename; // Relative path
                        if (file_exists($imagePath)) 
                        {
                            $imagePath .= '?' . filemtime($imagePath);
                            echo "<h3> Signal 1 minuter innan 1a start </h3>";
                            echo "<img id='$filename' src='$imagePath' alt='1a_start 1 min picture' width='640' height='480'>";

                            // Check and display the start image
                            $filename = '1a_start_Start.jpg';
                            $imagePath = 'images/' . $filename; // Relative path
                            if (file_exists($imagePath)) 
                            {
                                $imagePath .= '?' . filemtime($imagePath);
                                echo "<h3> Foto vid 1a start $start_time </h3>";
                                echo "<img id='$filename' src='$imagePath' alt='1a start picture' width='640' height='480'>";
                            } else {
                                console_log('picture for the start do not exists');
                            }
                        } else {
                            console_log('picture 1 min do not exists');
                        }
                    } else {
                        console_log('picture 4 min do not exists');
                    }
                } else {
                    //console_log('picture 5 min do not exists');
                }
            ?>
        </div> 
        <!-- Display pictures for the 2nd start -->
        <div style="text-align: center;">
            <?php
                //if ($num_starts == 2)
                {
                    $filename = '1a_start_Start.jpg';
                    $imagePath = 'images/' . $filename; // Relative path
                    if (file_exists($imagePath)) 
                    {
                        // Check and display the first image
                        $filename = '2a_start_5_min.jpg';
                        $imagePath = 'images/' . $filename; // Relative path
                        if (file_exists($imagePath)) {
                            $imagePath .= '?' . filemtime($imagePath);
                            echo "<h3> Bilder tagna vid varje signal innan 2a start  </h3> ";
                            echo "<br> ------------------------------------------------- <p></p> ";
                            echo "<h3> Varningssignal 5 minuter innan 2a start</h3>";
                            echo "<img id='$filename' src='$imagePath' alt='2a_start 5 min picture' width='640' height=480'>";

                            // Check and display the second image
                            $filename = '2a_start_4_min.jpg';
                            $imagePath = 'images/' . $filename; // Relative path
                            if (file_exists($imagePath)) {
                                $imagePath .= '?' . filemtime($imagePath);
                                echo "<h3> Signal 4 minuter innan 2a start </h3>";
                                echo "<img id='$filename' src='$imagePath' alt='2a_start 4 min picture' width='640' height='480'>";

                                // Check and display the third image
                                $filename = '2a_start_1_min.jpg';
                                $imagePath = 'images/' . $filename; // Relative path
                                if (file_exists($imagePath)) {
                                    $imagePath .= '?' . filemtime($imagePath);
                                    echo "<h3> Signal 1 minuter innan 2a start </h3>";
                                    echo "<img id='$filename' src='$imagePath' alt='2a_start 1 min picture' width='640' height='480'>";

                                    // Check and display the start image
                                    $filename = '2a_start_Start.jpg';
                                    $imagePath = 'images/' . $filename; // Relative path
                                    if (file_exists($imagePath)) {
                                        $imagePath .= '?' . filemtime($imagePath);
                                        echo "<h3> Foto vid 2a start $second_start_time </h3>";
                                        echo "<img id='$filename' src='$imagePath' alt='2a start picture' width='640' height='480'>";
                                    } else {
                                        console_log('picture start 2nd start do not exists');
                                    }
                                } else {
                                    console_log('picture 1 min 2nd start do not exists');
                                }
                            } else {
                                console_log('picture 4 min 2nd start do not exists');
                            }
                        } else {
                            console_log('picture 5 min 2nd start do not exists');
                        }
                    }
                }
            ?>
        </div>
        <!-- Display of video0 when it is available -->
        <div style="text-align: center;" class="w3-panel w3-pale-blue">
            <?php
                // check if 1 or 2 starts
                if ($num_starts == 2) 
                { 
                    // Check and display the start image
                    if (file_exists('images/2a_start_Start.jpg'))
                    {
                        $video_name = 'images/video0.mp4';
                        if (file_exists($video_name)) {
                            echo "<h4> Video från 5 min före start och 2 min efter sista start</h4>";
                            echo '<video id="video0" width = "640" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
                        } else {
                            console_log("$video_name do not exists");
                        }
                    }
                } else {
                    // Check if first start image exists
                    if (file_exists('images/1a_start_Start.jpg'))
                    {
                        $video_name = 'images/video0.mp4';
                        if (file_exists($video_name)) {
                            //console_log("$video_name "is available");
                            echo "<h4> Video från 5 min före start och 2 min efter start</h4>";
                            echo '<video id="video0" width = "640" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
                        } else {
                            console_log("$video_name do not exists");
                        }
                    }
                }
            ?>
        </div>
        <!-- PHP script to show "Stop recording" button after video0 is ready -->
        <div style="text-align: center;" class="w3-panel w3-pale-green">
            <?php
                if ($num_video == 1) // which is valid for regattastart9 and not selectable 
                {
                    // Check the Stop Recording button state
                    $stopRecordingPressed = isset($_SESSION['stopRecordingPressed']) ? $_SESSION['stopRecordingPressed'] : false;
                    $status_file = '/var/www/html/status.txt'; // Check recording status from status.txt
                    $videoComplete = file_exists($status_file) && trim(file_get_contents($status_file)) === 'complete';

                    // Show Stop Recording button only if video still being recored
                    if (!$videoComplete && $video0Exists) 
                    {
                        echo '<div id="stopRecordingButtonDiv">';
                        if (!$stopRecordingPressed) 
                        {
                            echo '<form id="stopRecordingForm" method="post">
                                    <input type="hidden" name="stop_recording" value="true">
                                    <input type="hidden" id="stopRecordingPressed" name="stopRecordingPressed" value="0">
                                    <input type="submit" id="stopRecordingButton" value="Stop Recording">
                                </form>';
                        }
                        echo '</div>';
                    } else {
                        echo '<div id="stopRecordingButtonDiv" style="display:none;"></div>';
                    }
                }
            ?>
        </div>
        <!-- Display of video1 when it is available in w3-pale-red section -->
        <!-- PHP script to display video1 area (red panel) -->
        <?php
        if ($video0Exists) {
            echo '<div class="w3-panel w3-pale-red" style="text-align:center; padding:20px;">';

            if ($num_video == 1) {
                // --- Regattastart9/10 (only one video expected) ---
                $stopRecordingPressed = $_SESSION['stopRecordingPressed'] ?? false;
                $status_file = '/var/www/html/status.txt';
                $videoComplete = file_exists($status_file) && trim(file_get_contents($status_file)) === 'complete';
                $video1File = 'images/video1.mp4';

                if (!$stopRecordingPressed) {
                    // Case 2: Recording ongoing, before stop pressed
                    echo '<form id="stopRecordingForm" method="post">
                            <input type="hidden" name="stop_recording" value="true">
                            <input type="hidden" id="stopRecordingPressed" name="stopRecordingPressed" value="0">
                            <input type="submit" id="stopRecordingButton" value="Stop Recording">
                        </form>';
                    echo '<p style="font-size:18px;color:#555;">Recording in progress...</p>';

                } elseif ($stopRecordingPressed && !$videoComplete) {
                    // Case 3: Stop pressed, waiting for processing
                    echo '<div id="videoStatusDiv">
                        <p id="statusText" style="font-size:18px;color:#555;">Video being created...</p>
                    </div>';
                } elseif ($videoComplete && file_exists($video1File) && filesize($video1File) > 1000) {
                    // Case 4: Video complete, show player
                    echo "<h3>Finish video (video1.mp4)</h3>";
                    echo '<video id="video1" width="640" height="480" controls>
                            <source src="' . $video1File . '" type="video/mp4">
                        </video>';

                } else {
                    // Fallback if file missing or too small
                    echo '<p style="font-size:18px;color:#555;">Recording finished, but no valid video produced.</p>';
                }

            } else {
                // --- Regattastart6 (multiple videos) ---
                for ($x = 1; $x <= $num_video; $x++) {
                    $video_name = "images/video$x.mp4";
                    if (file_exists($video_name) && filesize($video_name) > 1000) {
                        echo "<h3>Finish video $x</h3>";
                        echo '<video id="video' . $x . '" width="640" height="480" controls>
                                <source src="' . $video_name . '" type="video/mp4">
                            </video><p>';
                    } else {
                        echo "<p style='font-size:18px;color:#555;'>Video $x not available or incomplete.</p>";
                    }
                }
            }

            echo '</div>'; // end pale-red panel
        }
        ?>
        <script>
        <?php if ($num_video == 1 && ($stopRecordingPressed && !$videoComplete)): ?>
        // JavaScript to poll for video1 completion (only for regattastart9/10)
        function pollVideoStatus() {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/status.txt?rand=' + Math.random(), true); // cache-buster
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    var status = xhr.responseText.trim();
                    if (status === 'complete') {
                        // Replace the placeholder with the video
                        var div = document.getElementById('videoStatusDiv');
                        if (div) {
                        div.innerHTML = '<h3>Finish video (video1.mp4)</h3>' +
                                        '<video id="video1" width="640" height="480" controls>' +
                                        '<source src="images/video1.mp4" type="video/mp4">' +
                                        '</video>';
                    }
                    } else {
                        // check again in 2 seconds
                        setTimeout(pollVideoStatus, 2000);
                    }
                } else if (xhr.readyState === 4) {
                    // HTTP error: try again
                    setTimeout(pollVideoStatus, 2000);
                }
            };
            xhr.send();
        }

        // Start polling automatically
        pollVideoStatus();
        <?php endif; ?>
        </script>
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
    <!-- JavaScript to step frames in videos -->
    <script> // function to step frames 
        function stepFrame(videoNum, step) {
            var video = document.getElementById('video' + videoNum);
            if (video) {
                video.pause();
                video.currentTime += step * (1 / video.playbackRate/5); // 
            }
        }
    </script>
    <!-- JavaScript to refresh the page after the "Refresh" button was pressed -->
    <script>
        function refreshThePage() {
                setTimeout(function() {
                    location.reload();
                }, 1000); // 1 sec
            }
    </script>
    <!-- JavaScript: Poll for video1 completion (only for regattastart9/10) -->
    <?php if ($num_video == 1): ?>
        <script>
        function checkVideoStatus() {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/status.txt', true);
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    var status = xhr.responseText.trim();
                    if (status === 'complete') {
                        console.log("Video complete! Reloading page...");
                        location.reload();  // show video1.mp4
                    } else {
                        // Not complete yet: check again after 2 seconds
                        setTimeout(checkVideoStatus, 2000);
                    }
                } else if (xhr.readyState === 4) {
                    // HTTP error: try again after 2 seconds
                    setTimeout(checkVideoStatus, 2000);
                }
            };
            xhr.send();
        }

        // Start polling only if Stop Recording button was pressed
        var stopPressedInput = document.getElementById("stopRecordingPressed");
        if (stopPressedInput && stopPressedInput.value === "1") {
            console.log("Stop Recording pressed, starting to poll for video completion...");
            checkVideoStatus();
        }

        // Optional: set hidden input to 1 when button is pressed
        var stopButton = document.getElementById("stopRecordingButton");
        if (stopButton) {
            stopButton.addEventListener('click', function() {
                stopPressedInput.value = "1";
                console.log("Stop Recording button clicked: stopRecordingPressed=1");
            });
        }
        </script>
    <?php endif; ?>
</body>
</html>