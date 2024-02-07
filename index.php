<?php
    define('APP_VERSION', '24.02.06'); // You can replace '1.0.0' with your desired version number
    session_id("regattastart");
    session_start();
    // after "git pull", "sudo cp /home/pi/Regattastart/index.php /var/www/html/"
    ini_set('display_errors', 1); 
    error_reporting(E_ALL);
    print_r($_SESSION);
    echo "<br/>";
    print_r($_POST);
    echo "<br/>";
?>
<?php
    if ($_SERVER["REQUEST_METHOD"] === "POST") {
        // Form was submitted
        include "stop_recording.php"; // Include the script to stop recording
        error_log('Line 13: The stop_recording.php was included in index.php');
        // exit; // Stop further execution after including the script
    } elseif ($_SERVER["REQUEST_METHOD"] !== "GET") {
        // Log an error only if the request method is neither "POST" nor "GET"
        error_log('Line 16: $_SERVER["REQUEST_METHOD"] < > "POST" NOR "GET" ');
    }
?>
<!-- Your HTML to display data from the session -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- meta http-equiv="refresh" content="200" -->
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
<!-- Text on top of page retrieved from index6 or index9 -->
<?php
    if (isset($_SESSION['form_data']) && is_array($_SESSION['form_data'])) {

        if (array_key_exists('start_time', $_SESSION['form_data'])) {
            // Retrieve the value of the 'start_time' key
            $start_time = $_SESSION['form_data']['start_time'];
            echo "First start time: " . $start_time;
        }
        if (array_key_exists('video_end', $_SESSION['form_data'])) {
            $video_end = $_SESSION['form_data']['video_end'];
            echo " Video end duration: " . $video_end;
        }
        if (array_key_exists('num_starts', $_SESSION['form_data'])) {
            $num_starts = $_SESSION['form_data']['num_starts'];
            echo " Number of starts: $num_starts";
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
        echo "No form data found in the session.";
    }
?>
<header>
    <div style="text-align: center;">
        <div id="image-container">
            <!-- Your image elements will be added here dynamically -->
        </div>
    </div>
</header>
<!-- Here is our page's main content -->
<main>
    <div style="text-align: center;">
        <h4><a href="/index6.php" title="Regattastart6 "> Two starts -- Regattastart6 </a></h4>
    </div>
    <div style="text-align: center;">
        <h4><a href="/index9.php" title="Setup page Regattastart9">  Regattastart9 -- with image detection </a></h4>
    </div> 
    <!-- Stop recording button -->
    <div style="text-align: center;" class="w3-panel w3-pale-green">
        <?php
            $video_name = 'images/video0.mp4';
            if (file_exists($video_name)) {
                echo "<h4> Efter sista båt i mål, kan man stoppa och generera video för målgång </h4>";
                echo '<div id="stopRecordingButtonDiv">
                    <form id="stopRecordingForm" action="' . htmlspecialchars($_SERVER["PHP_SELF"]) . '" method="post">
                        <input type="submit" id="stopRecordingButton" value="Stop Recording">
                    </form>
                </div>';
            }
        ?>
    </div>
    <!-- remaining videos -->
    <div style="text-align: center;" class="w3-panel w3-pale-red">
        <?php
            $video_name = 'images/video1.mp4';
            if (file_exists($video_name)) {
                echo "<h3> Finish video, this is video $x for the finish</h3><br>";
                echo '<div>
                <video id="video1.mp4" width="720" height="480" controls>
                    <source src="' . $video_name . '" type="video/mp4">
                </video>
            </div>';
            }
        ?>
    </div>
    <!-- function to hide the tecording button -->
    <script>
        // Function to hide the stop recording button after it's pressed
        function hideStopRecordingButton() {
            var stopRecordingButtonDiv = document.getElementById('stopRecordingButtonDiv');
            if (stopRecordingButtonDiv) {
                stopRecordingButtonDiv.style.display = 'none';
            }
        }
        // Event listener to trigger hiding of the button when the form is submitted
        document.getElementById('stopRecordingForm').addEventListener('submit', function() {
            hideStopRecordingButton();
        });
    </script>
    </main>
</body>
</html>