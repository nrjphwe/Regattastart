<?php
    header("Access-Control-Allow-Origin: *");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: *");
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    define('APP_VERSION', '24.02.23'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    ini_set('display_errors', 1); 
    error_reporting(E_ALL);
    // Check if video0.mp4 or video1.mp4 exists 
    $video0Exists = file_exists("images/video0.mp4");
    $video1Exists = file_exists("images/video1.mp4");
    error_log("Line  14: video0Exists =" . $video0Exists);
    error_log("Line  15: video1Exists =" . $video1Exists);

    # initialize the status for Stop_recording button
    $stopRecordingPressed = false;

    // Retrieve session data
    $formData = isset($_SESSION['form_data']) && is_array($_SESSION['form_data']) ? $_SESSION['form_data'] : [];

    // Extract relevant session data
    extract($formData); // This will create variables like $start_time, $video_end, etc.

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['stop_recording'])) 
    {
        // Handle stop recording logic here
        include_once "stop_recording.php"; // Include the script to stop recording
        error_log('Line 30: The stop_recording.php was included in index.php');
        $stopRecordingPressed = true;
        // Store this value in a session to persist it across requests
        $_SESSION['stopRecordingPressed'] = $stopRecordingPressed;
    }
?>
<?php 
    function isVideo1Completed() {
        // Read the content of the status file
        $status = trim(file_get_contents('/var/www/html/status.txt'));
        // Check if the status indicates Video1 completion
        return ($status === 'complete');
    }
    // Check Video1 completion status
    $video1Completed = isVideo1Completed();

    // Return the completion status as JSON
    echo json_encode($video1Completed);
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
    <!--link rel="icon" type="image/x-icon" href="/images/sailing-icon.ico"-->
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
    <?php // Print session data on top of page
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
            echo ", Video end duration :  $video_end + 2 minutes after start";
        }
        // Determine the number of videos during finish if not set, 
        // regattastart9 is executing and num_video is set to 1 as a flag.
        // This function checks if the variable $num_video is set
        $num_video = isset($num_video) ? $num_video : 1;
    ?>
    <!-- Header content -->
    <header>
        <div style="text-align: center;">
            <div class="w3-panel w3-teal">
                <h2> Regattastart  </h2>
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
                    echo "<img id='$filename' src='$imagePath' alt='1a_start 5 min picture' width='720' height='480'>";

                    // Check and display the second image
                    $filename = '1a_start_4_min.jpg';
                    $imagePath = 'images/' . $filename; // Relative path
                    if (file_exists($imagePath)) 
                    {
                        $imagePath .= '?' . filemtime($imagePath);
                        echo "<h3> Signal 4 minuter innan 1a start </h3>";
                        echo "<img id='$filename' src='$imagePath' alt='1a_start 4 min picture' width='720' height='480'>";

                        // Check and display the third image
                        $filename = '1a_start_1_min.jpg';
                        $imagePath = 'images/' . $filename; // Relative path
                        if (file_exists($imagePath)) 
                        {
                            $imagePath .= '?' . filemtime($imagePath);
                            echo "<h3> Signal 1 minuter innan 1a start </h3>";
                            echo "<img id='$filename' src='$imagePath' alt='1a_start 1 min picture' width='720' height='480'>";

                            // Check and display the start image
                            $filename = '1a_start_Start.jpg';
                            $imagePath = 'images/' . $filename; // Relative path
                            if (file_exists($imagePath)) 
                            {
                                $imagePath .= '?' . filemtime($imagePath);
                                echo "<h3> Foto vid 1a start $start_time </h3>";
                                echo "<img id='$filename' src='$imagePath' alt='1a start picture' width='720' height='480'>";
                            } else {
                                error_log('Line 218: picture for the start do not exists');
                            }
                        } else {
                            error_log('Line 221: picture 1 min do not exists');
                        }
                    } else {
                        error_log('Line 224: picture 4 min do not exists');
                    }
                } else {
                    //error_log('Line 227: picture 5 min do not exists');
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
                            echo "<img id='$filename' src='$imagePath' alt='2a_start 5 min picture' width='720' height=480'>";

                            // Check and display the second image
                            $filename = '2a_start_4_min.jpg';
                            $imagePath = 'images/' . $filename; // Relative path
                            if (file_exists($imagePath)) {
                                $imagePath .= '?' . filemtime($imagePath);
                                echo "<h3> Signal 4 minuter innan 2a start </h3>";
                                echo "<img id='$filename' src='$imagePath' alt='2a_start 4 min picture' width='720' height='480'>";

                                // Check and display the third image
                                $filename = '2a_start_1_min.jpg';
                                $imagePath = 'images/' . $filename; // Relative path
                                if (file_exists($imagePath)) {
                                    $imagePath .= '?' . filemtime($imagePath);
                                    echo "<h3> Signal 1 minuter innan 2a start </h3>";
                                    echo "<img id='$filename' src='$imagePath' alt='2a_start 1 min picture' width='720' height='480'>";

                                    // Check and display the start image
                                    $filename = '2a_start_Start.jpg';
                                    $imagePath = 'images/' . $filename; // Relative path
                                    if (file_exists($imagePath)) {
                                        $imagePath .= '?' . filemtime($imagePath);
                                        echo "<h3> Foto vid 2a start $second_start_time </h3>";
                                        echo "<img id='$filename' src='$imagePath' alt='2a start picture' width='720' height='480'>";
                                    } else {
                                        error_log('Line 274: picture start 2nd start do not exists');
                                    }
                                } else {
                                    error_log('Line 277: picture 1 min 2nd start do not exists');
                                }
                            } else {
                                error_log('Line 280: picture 4 min 2nd start do not exists');
                            }
                        } else {
                            error_log('Line 283: picture 5 min 2nd start do not exists');
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
                            echo '<video id="video0" width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
                        } else {
                            error_log("Line 303: $video_name do not exists");
                        }
                    }
                } else {
                    // Check if first start image exists
                    if (file_exists('images/1a_start_Start.jpg'))
                    {
                        $video_name = 'images/video0.mp4';
                        if (file_exists($video_name)) {
                            //error_log("Line 316: $video_name is available");
                            echo "<h4> Video från 5 min före start och 2 min efter start</h4>";
                            echo '<video id="video0" width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
                        } else {
                            error_log("Line 316: $video_name do not exists");
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
                            echo '
                                <form id="stopRecordingForm" action="' . htmlspecialchars($_SERVER["PHP_SELF"]) . '" method="post" onsubmit="return refreshPage()">
                                    <input type="hidden" name="stop_recording" value="true">
                                    <input type="hidden" name="stopRecordingPressed" id="stopRecordingPressed" value="0"> <!-- Hidden input field for stopRecordingPressed -->
                                    <input type="submit" id="stopRecordingButton" value="Stop Recording">
                                </form>
                            </div>';
                            //  "Stop Recording" button not yet visible
                            error_log("Line 344: stopRecording button not yet pressed");
                        }
                    } else {
                       // Log an information that video0 is not ready
                       error_log("Line 348: video0 is not available");
                    }
                } else {
                    // Log an error if $num_video is not equal to 1
                    error_log("Line 352: num_video = $num_video which is not 1");
                }
            ?>
        </div>
        <!-- PHP script to display remaining videos -->
        <div style="text-align: center;" class="w3-panel w3-pale-red">
            <?php
                if ($video0Exists)
                {
                    // wait with check until after the stop-recording button was pressed
                    if ($video1Exists){
                        for ($x = 1; $x <= $num_video; $x++) 
                        {
                            $video_name = 'images/video' . $x . '.mp4';
                            // error_log("Line 380: Loop to display video = $video_name");
                            if (file_exists($video_name)) 
                            {
                                // Display the video
                                echo "<h3> Finish video, this is video $x for the finish</h3>";
                                echo '<video id="video' . $x . '" width="720" height="480" controls>
                                <source src="' . $video_name . '" type="video/mp4"></video><p>
                                    <div>
                                        <button onclick="stepFrame(' . $x . ', -1)">Previous Frame</button>
                                        <button onclick="stepFrame(' . $x . ', 1)">Next Frame</button>
                                    </div>';
                            } else {
                                // Log an error if the video file doesn't exist
                                error_log("Line 379: video $x does not exist");
                            }
                        }
                    } else {
                        error_log("Line 383: Video1 do not exist");
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
                error_log("Line 424: $filename do not exists");
            }
        ?>
    </div>
    <div style="text-align: center;" class="w3-panel w3-grey">
        <?php 
            echo " Time now: " .date("H:i:s");
        ?> 
    </div>
    <!--- Java Scripts  -->
    <script>
        //var stopRecordingPressed = <?php echo json_encode($stopRecordingPressed); ?>; // Get the value from PHP
        var video0Exists= <?php echo json_encode($video0Exists); ?>; // Get the value from PHP
        console.log('Line 410: Video0Exists = ', video0Exists);

        if (video0Exists){
            // Automatic refresh after 5 seconds
            setTimeout(function() {
                location.reload();
            }, 5000); // 5 seconds
            video0Exists = 0;
        }
    </script>
    <script>
        var video1Exist = <?php echo json_encode($video1Exists); ?>; // Get the value from PHP
        console.log('Line 412: Video1Exists = ', video1Exist);
    </script>
    <script> // Function to check Video1 completion status and reload page if complete
        var checkCompletionInterval;

        function checkVideoCompletion() {
            // AJAX call to PHP script to check completion status
            $.ajax({
                url: window.location.href,
                type: 'GET',
                success: function(response) {
                    var trimmed_response = response.trim(); // Trim the response text
                    //console.log('Line 429: Video completion check response:', trimmed_response);
                    // If Video1 is completed, reload the page
                    if (trimmed_response === 'true') {
                        console.log('Line 431: Reloading page...');
                        location.reload(true); // Reload with hard refresh
                    } else {
                        console.log('Line 434: Video not completed yet.');
                        //location.reload(); // Reload
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Line 440: Error checking video completion:', error);
                }
            });
        }
        if (video1Exist) 
        {
        } else {
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
                video.currentTime += step * (1 / video.playbackRate/20); // 
            }
        }
    </script>
    <!-- JavaScript to automatically refresh the page after the "Stop Recording" button is pressed -->
    <script>
        var stopRecordingPressed;
        // This function executes AFTER the stop_recording button on Line 349 is pushed
        function refreshPage() {
            // Wait until after the Stop_Recording button was pressed
            alert("Wait a while after button was pressed!");
            if (stopRecordingPressed) {
                // Set the value of the hidden input field
                document.getElementById("stopRecordingPressed").value = "1"; // Set stopRecordingPressed value to 1
                console.log("Line 471: stopRecordingPressed value:", stopRecordingPressed); // Log the value
                document.getElementById("stopRecordingButton").style.display = "none";
                stopRecordingPressed = true;
                // Reload the page after 30 seconds, but only do it once
                setTimeout(function() {
                    location.reload();
                }, 60000); // 60 sec
            }
        }
    </script>
</body>
</html>