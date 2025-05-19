<?php
    // /var/log/php_error.log
    header("Access-Control-Allow-Origin: *");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: *");
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    define('APP_VERSION', '2025.03.26'); // You can replace '1.0.0' with your desired version number

    if (session_status() !== PHP_SESSION_ACTIVE) {
        // Set session parameters
        ini_set('session.gc_maxlifetime', 86400); // 24 hours
        session_set_cookie_params(86400); // 24 hours
        ini_set('session.cookie_lifetime', 86400);
    }
    if (session_status() === PHP_SESSION_NONE) {
        session_id("regattastart");
        session_start();
    }


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
    <link rel="icon" type="image/x-icon" href="/sailing-icon.ico">
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
        if ($num_starts == 2) {
            if (isset($dur_between_starts)) {
                echo ", Duration between starts: $dur_between_starts min";

                // Convert start time to minutes
                list($start_hour, $start_minute) = explode(':', $start_time);
                $start_time_minutes = $start_hour * 60 + $start_minute;

                // Calculate second start time in minutes
                $second_start_time_minutes = $start_time_minutes + $dur_between_starts;

                // Convert second start time back to hours and minutes
                $second_start_hour = floor($second_start_time_minutes / 60);
                $second_start_minute = $second_start_time_minutes % 60;

                // Format second start time
                $second_start_time = sprintf('%02d:%02d', $second_start_hour, $second_start_minute);
                echo ", 2nd Start at: $second_start_time";
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
            $start_time_minutes = $start_hour * 60 + $start_minute;

            // Add video_end (duration after start) and additional 2 minutes
            $video_end_time_minutes = $start_time_minutes + $video_end + 2;

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
                    echo "<img id='$filename' src='$imagePath' alt='1a_start 5 min picture' width='640' height='406'>";

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
                if ($num_starts == 2)
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
                    // Retrieve the value of the session variable
                    $stopRecordingPressed = isset($_SESSION['stopRecordingPressed']) ? $_SESSION['stopRecordingPressed'] : false;
                    if ($video0Exists) // stop-recording button should not be visible unless the video0 exists
                    {
                        if ($stopRecordingPressed) // If button was pressed hide button
                        {
                            echo '<div id="stopRecordingButtonDiv" style="display: none;">'; // Hide the div
                        } else {
                            echo '<div id="stopRecordingButtonDiv" style="display: block;">'; // Display the div
                            echo "
                                <form id=\"stopRecordingForm\" action=\"" . htmlspecialchars($_SERVER["PHP_SELF"]) . "\" method=\"post\" onsubmit=\"return refreshPage()\">
                                    <input type=\"hidden\" name=\"stop_recording\" value=\"true\">
                                    <input type=\"hidden\" name=\"stopRecordingPressed\" id=\"stopRecordingPressed\" value=\"0\"> 
                                    <!-- Hidden input field for stopRecordingPressed -->
                                    <input type=\"submit\" id=\"stopRecordingButton\" value=\"Stop Recording\">
                                </form>
                            </div>";
                            //  "Stop Recording" button not yet visible
                            console_log("stopRecording button not yet pressed");
                        }
                    } else {
                       // Log an information that video0 is not ready
                       console_log("video0 is not available");
                    }
                } else {
                    // Log an error if $num_video is not equal to 1
                    console_log("num_video = $num_video which is not 1");
                }
            ?>
        </div>
        <!-- PHP script to display remaining videos -->
        <div style="text-align: center;" class="w3-panel w3-pale-red", style="display: inline-block; padding: 20px;">
            <?php
                $video_avi = 'images/video1.avi';
                $video_mp4 = 'images/video1.mp4';
                if ($video0Exists)
                {
                    // wait with check until after the stop-recording button was pressed
                    if ($video1Exists){
                        for ($x = 1; $x <= $num_video; $x++) 
                        {
                            $video_name = 'images/video' . $x . '.mp4';
                            // console_log("Loop to display video = $video_name");
                            if (file_exists($video_name) && filesize($video_name) > 1000)
                            {
                                // Display the video
                                echo "<h3> Finish video, this is video $x for the finish</h3>";
                                echo '<video id="video' . $x . '" width="640" height="480" controls>
                                <source src="' . $video_name . '" type="video/mp4"></video><p>
                                    <div>
                                        <button onclick="stepFrame(' . $x . ', -1)">Previous Frame</button>
                                        <button onclick="stepFrame(' . $x . ', 1)">Next Frame</button>
                                    </div>';
                            }
                        }
                    } elseif (file_exists($video_avi) && filesize($video_avi) > 5500) {
                    // AVI exists but MP4 is not done or still 0 KB → still recording/detecting
                    echo '<div style="width:640px;height:480px;display:flex;align-items:center;justify-content:center;background:#eee;border:1px solid #ccc;">
                            <p style="font-size:20px;color:#555;">Video being created...</p>
                        </div>';
                    } else {
                        // Neither usable .mp4 nor active .avi → nothing detected
                        echo '<div style="width:640px;height:480px;display:flex;align-items:center;justify-content:center;background:#eee;border:1px solid #ccc;">
                                <p style="font-size:20px;color:#555;">No boat detected</p>
                            </div>';
                        console_log("Video1 do not exist");
                    }
                }
            ?>
        </div>
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
    <!--- Java Scripts  -->
    <script> // Function to check Video1 completion status and reload page if complete
        //var checkCompletionInterval;
        var video1Exists = <?php echo json_encode($video1Exists); ?>; // Get the value from PHP 
        //console.log('index.php, function response=', video1Exists);

        function checkVideoCompletion() {
            // AJAX call to PHP script to check completion status
            $.get('check_video_completion.php', function(response, status) {
                //alert("Data: " + response + "\nStatus: " + status);
                var trimmed_response = response.trim(); // Trim the response text
                // If Video1 is completed, reload the page
                if (trimmed_response === 'complete') {
                    console.log('checkVideo OK, Reloading page...');
                    location.reload(true); // Reload with hard refresh
                } else {
                    console.log('Video1 not completed yet.');
                    // Handle the case when Video1 is not completed yet
                }
            }).fail(function(xhr, status, error) {
                 console.error('AJAX failed:', error);
            });
        }
        if (!video1Exists) 
        {
            // Start interval to check completion every 60 seconds
            checkCompletionInterval = setInterval(checkVideoCompletion, 60000); // Check every 60 seconds
        }
    </script>
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
    <!-- java script that executes AFTER the stop_recording button on Line 340 was pushed -->
    <script>
         var stopRecordingPressed;

        function refreshPage() {
            // Wait until after the Stop_Recording button was pressed
            // alert("Wait a while after button was pressed!");
            if (stopRecordingPressed) {
                // Set the value of the hidden input field
                document.getElementById("stopRecordingPressed").value = "1"; // Set stopRecordingPressed value to 1
                console.log("stopRecordingPressed value:", stopRecordingPressed); // Log the value
                document.getElementById("stopRecordingButton").style.display = "none";
                stopRecordingPressed = true;
                // Reload the page after 60 seconds
                setTimeout(function() {
                    location.reload(true);
                }, 60000); // 60 sec
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
</body>
</html>