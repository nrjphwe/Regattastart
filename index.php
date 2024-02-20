<?php
    define('APP_VERSION', '24.02.06'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    ini_set('display_errors', 1); 
    error_reporting(E_ALL);
?>
<?php // Stop-recording form was submitted 
    // Check if video0.mp4 exists
    $video0Exists = file_exists("images/video0.mp4");
    // Check if video1.mp4 exists
    $video1Exists = file_exists("images/video1.mp4");

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['stop_recording'])) {
        // Handle stop recording logic here
        include_once "stop_recording.php"; // Include the script to stop recording
        error_log('Line 19: The stop_recording.php was included in index.php');
        header("Location: {$_SERVER['PHP_SELF']}");
        exit;
    }
?>
<!-- Your HTML to display data from the session -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- <meta http-equiv="refresh" content="200" -->
    <title>Regattastart</title>
    <!-- JavaScript to dynamically add a placeholder text or an image to the page when -->
    <!-- there are no pictures available yet. -->
    <!-- function showPlaceholder -->
    <script>
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
    <link rel="stylesheet" href="/w3.css">
</head>
<body onload="showPlaceholder()">
<?php // Data on top of page retrieved from index6 or index9
    if (isset($_SESSION['form_data']) && is_array($_SESSION['form_data'])) {

        if (array_key_exists('start_time', $_SESSION['form_data'])) {
            // Retrieve the value of the 'start_time' key
            $start_time = $_SESSION['form_data']['start_time'];
            echo "First start time: " . $start_time;
        }
        if (array_key_exists('video_end', $_SESSION['form_data'])) {
            $video_end = $_SESSION['form_data']['video_end'];
            echo ", Video end duration :  $video_end + 2 minutes after start, ";
        }
        if (array_key_exists('num_starts', $_SESSION['form_data'])) {
            $num_starts = $_SESSION['form_data']['num_starts'];
            echo " Number of starts: $num_starts";
        }
        if ($num_starts == 2) {
            if (array_key_exists('dur_between_starts', $_SESSION['form_data'])) {
                $dur_between_starts = $_SESSION['form_data']['dur_between_starts'];
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
        if (array_key_exists('video_dur', $_SESSION['form_data'])) {
            $video_dur = $_SESSION['form_data']['video_dur'];
            echo " Video duration: $video_dur";
        }
        if (array_key_exists('video_delay', $_SESSION['form_data'])) {
            $video_delay = $_SESSION['form_data']['video_delay'];
            echo " Video delay after start: " . $video_delay;
        }
        if (array_key_exists('num_video', $_SESSION['form_data'])) {
            $num_video = $_SESSION['form_data']['num_video'];
            echo " Number of videos during finish: " . $num_video;
        } else {
            $num_video = 1;
        }
    }
    else {
        // 'form_data' array not set or not an array
        echo "Line 116: No form data found in the session.";
    }
?>
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
    <!-- Bilder tagna vid varje signal innan start  -->
    <div style="text-align: center;" class="w3-panel w3-pale-blue">
        <h3> Bilder tagna vid varje signal innan 1a start </h3>
    </div>
    <!-- Pictures for the 1st start  -->
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
                error_log('Line 191: picture 5 min do not exists');
            }
        ?>
    </div> 
    <!-- Pictures for the 2nd start -->
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
                                error_log('Line 243: picture start 2nd start do not exists');
                            }
                        } else {
                            error_log('Line 246: picture 1 min 2nd start do not exists');
                        }
                    } else {
                        error_log('Line 249: picture 4 min 2nd start do not exists');
                    }
                } else {
                    error_log('Line 252: picture 5 min 2nd start do not exists');
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
                if (file_exists($video_name)) {
                    //error_log("Line 256: $video_name is available");
                    echo "<h4> Video 5 min före start och 2 min efter, eller vid 2 starter, till 2 min efter andra start </h4>";
                    echo '<video id="video0" width = "720" height="480" controls><source src= ' . $video_name . ' type="video/mp4"></video><p>';
                } else {
                    error_log("Line 260: $video_name do not exists");
                }
            }
        ?>
    </div>
    <!-- Show "Stop recording" button after video0 is ready -->
    <div style="text-align: center;" class="w3-panel w3-pale-green">
        <?php
            if ($num_video == 1) {
                if ($video0Exists && !$video1Exists) {
                    // Show the "Stop Recording" button if video0.mp4 exists
                    echo '<div id="stopRecordingButtonDiv">
                        <form id="stopRecordingForm" action="' . htmlspecialchars($_SERVER["PHP_SELF"]) . '" method="post">
                            <input type="hidden" name="stop_recording" value="true">
                            <input type="submit" id="stopRecordingButton" value="Stop Recording">
                        </form>
                    </div>';
                }
            } else {
                // Log an error if $num_video is not equal to 1
                error_log("Line 280: $num_video is not 1");
            }
        ?>
    </div>
    <script> // JavaScript to periodically check for the existence of video0.mp4 and video1.mp4
        // This script runs every 5 seconds
        setInterval(function() {
            // Check if video0.mp4 exists
            var video0Exists = <?php echo json_encode($video0Exists); ?>;
            // Check if video1.mp4 exists
            var video1Exists = <?php echo json_encode($video1Exists); ?>;

            if (video0Exists) {
                // Show the "Stop Recording" button
                document.getElementById("stopRecordingButtonDiv").style.display = "block";
            } else {
                // Hide the "Stop Recording" button
                document.getElementById("stopRecordingButtonDiv").style.display = "none";
            }

            // If video1.mp4 exists, reload the page to stop the blocking period
            if (video1Exists) {
                location.reload();
            }
        }, 5000); // Check every 5 seconds

        // Function to hide the "Stop Recording" button after it's pressed
        document.getElementById("stopRecordingForm").addEventListener("submit", function() {
            document.getElementById("stopRecordingButtonDiv").style.display = "none";
        });
    </script>
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
                    error_log("Line 324: video1 do not exists");
                }
            }
        ?>
    </div>
    <script> // function to step frames 
        function stepFrame(videoNum, step) {
            var video = document.getElementById('video' + videoNum);
            if (video) {
                video.pause();
                video.currentTime += step * (1 / video.playbackRate/20); // 
            }
        }
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
            error_log("Line 348: $filename do not exists");
        }
        ?>
    </div>
    <div style="text-align: center;" class="w3-panel w3-grey">
        <?php 
            echo " Time now: " .date("H:i:s");
        ?> 
    </div>
</body>
</html>