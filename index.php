<?php
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    define('APP_VERSION', '24.02.06'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    ini_set('display_errors', 1); 
    error_reporting(E_ALL);

    // Check if video0.mp4 or video1.mp4 exists 
    $video0Exists = file_exists("images/video0.mp4");
    $video1Exists = file_exists("images/video1.mp4");

    // Check if the "Stop Recording" button was pressed
    //$stopRecordingPressed = isset($_POST['stopRecordingPressed']) && $_POST['stopRecordingPressed'] == "1";
    //error_log("Line 15: StopRecordingPressed set to: $stopRecordingPressed");
    // Retrieve session data
    $formData = isset($_SESSION['form_data']) && is_array($_SESSION['form_data']) ? $_SESSION['form_data'] : [];

    // Extract relevant session data
    extract($formData); // This will create variables like $start_time, $video_end, etc.

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['stop_recording'])) 
    {
        // Handle stop recording logic here
        include_once "stop_recording.php"; // Include the script to stop recording
        error_log('Line 26: The stop_recording.php was included in index.php');
        $stopRecordingPressed = True;
        // Store this value in a session to persist it across requests
        $_SESSION['stopRecordingPressed'] = $stopRecordingPressed;
    }
?>
<!-- Your HTML to display data from the session -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/w3.css">
    <!-- <meta http-equiv="refresh" content="200" -->
    <title>Regattastart</title>
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
    </style>
</head>
<body onload="showPlaceholder()">
    <?php // Print session data on top of page 
        echo "First start time: " . $start_time;
        echo ", Video end duration :  $video_end + 2 minutes after start, ";
        echo " Number of starts: $num_starts";
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
                echo ", 2nd Start is at: $second_start_time ";
            }
        }
        if (isset($video_dur)) {
            echo " Video duration: $video_dur";
            echo " Video delay after start: " . $video_delay;
            echo " Number of videos during finish: " . $num_video;
        }
        // Determine the number of videos during finish if not set, 
        // regattastart9 is executing and num_video is set to 1 as a flag.
        // This function checks if the variable $num_video is set
        $num_video = isset($num_video) ? $num_video : 1;
    ?>
    <!-- Header content -->
    <header>
        <div style="text-align: center;">
            <div class="w3-panel w3-blue">
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
        <!-- Link to index6 -->
        <div style="text-align: center;">
            <h4><a href="/index6.php" title="Regattastart6 "> Two starts -- Regattastart6 </a></h4>
        </div>
        <!-- Link to index9 -->
        <div style="text-align: center;">
            <h4><a href="/index9.php" title="Setup page Regattastart9">  Regattastart9 -- with image detection </a></h4>
        </div> 
        <!-- Bilder från varje signal innan start  -->
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
                    echo "<br> ------------------------------------------------- <p></p> ";
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
                                error_log('Line 182: picture for the start do not exists');
                            }
                        } else {
                            error_log('Line 185: picture 1 min do not exists');
                        }
                    } else {
                        error_log('Line 188: picture 4 min do not exists');
                    }
                } else {
                    //error_log('Line 191: picture 5 min do not exists');
                }
            ?>
        </div> 
        <!-- Display pictures for the 2nd start -->
        <div style="text-align: center;">
            <?php
                if ($num_starts == 2)
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
                                    error_log('Line 248: picture start 2nd start do not exists');
                                }
                            } else {
                                error_log('Line 251: picture 1 min 2nd start do not exists');
                            }
                        } else {
                            error_log('Line 254: picture 4 min 2nd start do not exists');
                        }
                    } else {
                        error_log('Line 257: picture 5 min 2nd start do not exists');
                    }
                }
            ?>
        </div>
        <!-- Display of video0 when it is available -->
        <div style="text-align: center;" class="w3-panel w3-pale-blue">
            <?php
                // Check and display the start image
                if (file_exists('images/1a_start_Start.jpg'))
                {
                    $video_name = 'images/video0.mp4';
                    if ($video0Exists) {
                        //error_log("Line 282: $video_name is available");
                        echo "<h4> Video från 5 min före start och 2 min efter sista start</h4>";
                        echo '<video id="video0" width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
                    } else {
                        error_log("Line 274: $video_name do not exists");
                    }
                }
            ?>
        </div>
        <!-- Show "Stop recording" button after video0 is ready -->
        <div style="text-align: center;" class="w3-panel w3-pale-green">
            <?php
                // Check if the "Stop Recording" button was pressed
                $stopRecordingPressed = isset($_POST['stopRecordingPressed']) && $_POST['stopRecordingPressed'] == "1";
                error_log("Line 275: StopRecordingPressed set to: $stopRecordingPressed");

                if ($num_video == 1) // which is valid for regattastart9 not selectable 
                {
                    if ($video0Exists && !$stopRecordingPressed) 
                    {
                        echo '<div id="stopRecordingButtonDiv" style="display: block;">'; // Display the div
                    } else {
                        echo '<div id="stopRecordingButtonDiv" style="display: none;">'; // Hide the div
                    }
                    echo '
                        <form id="stopRecordingForm" action="' . htmlspecialchars($_SERVER["PHP_SELF"]) . '" method="post" onsubmit="return refreshPage()">
                            <input type="hidden" name="stop_recording" value="true">
                            <input type="hidden" name="stopRecordingPressed" id="stopRecordingPressed" value="0"> <!-- Hidden input field for stopRecordingPressed -->
                            <input type="submit" id="stopRecordingButton" value="Stop Recording">
                        </form>
                    </div>';
                } else {
                    // Log an error if $num_video is not equal to 1
                    error_log("Line 287: $num_video is not 1");
                }
            ?>
        </div>
        <!-- Display remaining videos -->
        <div style="text-align: center;" class="w3-panel w3-pale-red">
            <?php
                if ($video0Exists)
                {
                    if ($video1Exists)
                    {
                        for ($x = 1; $x <= $num_video; $x++) {
                            $video_name = 'images/video' . $x . '.mp4';
                            // error_log("Line 307: Loop to display video = $video_name");
                            if (file_exists($video_name)) 
                            {
                                // Display the video
                                echo "<h3> Finish video, this is video $x for the finish</h3>";
                                echo '<video id="video' . $x . '" width="720" height="480" controls>
                                        <source src= ' . $video_name . ' type="video/mp4"></video><p>
                                    <div>
                                        <button onclick="stepFrame(' . $x . ', -1)">Previous Frame</button>
                                        <button onclick="stepFrame(' . $x . ', 1)">Next Frame</button>
                                    </div>';
                            } else {
                                // Log an error if the video file doesn't exist
                                error_log("Line 320: video $x does not exist");
                            }
                        }
                    } else {
                        error_log("Line 379: video1 do not exists");
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
                error_log("Line 348: $filename do not exists");
            }
        ?>
    </div>
    <div style="text-align: center;" class="w3-panel w3-grey">
        <?php 
            echo " Time now: " .date("H:i:s");
        ?> 
    </div>
    <!-- JavaScript to automatically refresh the page after the "Stop Recording" button is pressed -->
    <script>
        var stopRecordingPressed = <?php echo json_encode($stopRecordingPressed); ?>; // Get the value from PHP
        console.log("stopRecordingPressed value:", stopRecordingPressed); // Log the value
        
        function refreshPage() 
        {
            // Set the flag to true
            stopRecordingPressed = true;
            // Set the value of the hidden input field
            document.getElementById("stopRecordingPressed").value = "1"; // Set stopRecordingPressed value to 1
            console.log("stopRecordingPressed value:", stopRecordingPressed); // Log the value
            // Hide the button
            document.getElementById("stopRecordingButton").style.display = "none";
            setTimeout(function() {
                location.reload();
            }, 1000); // 1000 milliseconds = 1 second
        }

        // JavaScript to automatically refresh the page after a certain interval
        function autoRefresh() 
        {
            // Refresh the page after 60 seconds
            setTimeout(function() 
            {
                location.reload();
            }, 60000); // 60000 milliseconds = 60 seconds
        }
        // Call the autoRefresh function after the page is loaded
        window.onload = autoRefresh;

        // This script runs every 60 seconds to periodically check for the existence of video0.mp4 and video1.mp4
        setInterval(function() {
            // Check if video0.mp4 exists
            var video0Exists = <?php echo json_encode($video0Exists); ?>;
            // Check if video1.mp4 exists
            var video1Exists = <?php echo json_encode($video1Exists); ?>;
            
            console.log("video0Exists:", video0Exists);
            console.log("video1Exists:", video1Exists);
            console.log("stopRecordingPressed:", stopRecordingPressed);

            if (video0Exists && !stopRecordingPressed) {
                // Show the "Stop Recording" button if video0.mp4 exists and the button is not pressed
                document.getElementById("stopRecordingButtonDiv").style.display = "block";
            } else {
                // Hide the "Stop Recording" button otherwise
                document.getElementById("stopRecordingButtonDiv").style.display = "none";
            }

            // If video1.mp4 exists and stopRecordingPressed is true, hide the "Stop Recording" button
            // if (video1Exists && stopRecordingPressed) {
            if (video1Exists) {
                document.getElementById("stopRecordingButtonDiv").style.display = "none";
            }
        }, 60000); // Check every 60 seconds
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
</body>
</html>