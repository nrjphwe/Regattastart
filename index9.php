<?php
    header("Access-Control-Allow-Origin: *");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: *");

    define('APP_VERSION', '25.05.20'); // You can replace '1.0.0' with your desired version number

    // Set session lifetime to a day (86400 seconds)
    ini_set('session.gc_maxlifetime', 86400); // 24 hours
    session_set_cookie_params(86400); // 24 hours
    if (session_status() === PHP_SESSION_NONE) {
        session_id("regattastart");
        session_start();
    }

    ini_set('display_errors', 1);
    error_reporting(E_ALL);
    
    // Check if the session is already started
    print_r($_SESSION);
    echo "<br/>";
    print_r($_POST);
    echo "<br/>";

    // Unset the session variable set in index.php
    unset($_SESSION['stopRecordingPressed']);

    //if (isset($_SESSION["form_data"])) {
    //    echo '<pre>';
    //    print_r($_SESSION["form_data"]);
    //   echo '</pre>';
    //}
    include_once 'functions.php';
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // Process and store the form data
        $_SESSION["form_data"] = $_POST;

        // Execute the Python script
        #$command = 'python3 /usr/lib/cgi-bin/regattastart9.py ' . escapeshellarg(json_encode($_POST)) . ' > /var/www/html/output.txt 2>&1 &';
        $command = '/home/pi/yolov5_env/bin/python /usr/lib/cgi-bin/regattastart9.py ' . escapeshellarg(json_encode($_POST)) . ' > /var/www/html/output.txt 2>&1 &';

        shell_exec($command);
        echo date('h:i:s') . "<br>";
        echo "execution started";
        sleep(1);

        // Redirect to index.php
        header("Location: index.php");
        exit;
    }

    $day = date("l");
    //$start_time = "18:25"; // You need to initialize $start_time
    $video_end = isset($_SESSION["form_data"]["video_end"]) ? $_SESSION["form_data"]["video_end"] : "";
    $num_video = isset($_SESSION["form_data"]["num_video"]) ? $_SESSION["form_data"]["num_video"] : "";
    $num_starts = isset($_SESSION["form_data"]["num_starts"]) ? $_SESSION["form_data"]["num_starts"] : "";

?>
<!DOCTYPE html>
<head>
    <meta charset="UTF-8">
    <title> Regattastart9 image detection </title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/w3.css">
    <!-- set styles -->
    <style>
        /* Center align the content */
        .content-wrapper {
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }
        /* Ensure the form fields are displayed in a row */
        .w3-row-padding {
            display: flex;
            flex-wrap: wrap; /* Allow wrapping of elements */
            justify-content: space-around; /* Align elements evenly horizontally */
        }
        /* Style for individual form field containers */
        .w3-container {
            flex: 1; /* Let each container take up equal space */
            margin-bottom: 10px; /* Add some bottom margin for spacing between rows */
        }

        /* Adjust the width of the columns for smaller screens */
        @media screen and (max-width: 600px) {
            .w3-half {
                width: 100%; /* Make each column take up full width on smaller screens */
            }
        }
    </style>
</head>
<body>
<!-- Text on top of page retrieved from index6 or index9 -->
<div style="text-align: center;">
    <?php
    if (!function_exists('console_log')) {
        function console_log($message) {
            echo "<script>console.log(". json_encode($message) .");</script>";
        }
    }

    if (isset($_SESSION['form_data']) && is_array($_SESSION['form_data'])) {
        $start_time = $_SESSION['form_data']['start_time'] ?? "Not set";
        $video_end = $_SESSION['form_data']['video_end'] ?? "Not set";
        $num_starts = $_SESSION['form_data']['num_starts'] ?? "Not set";
        $dur_between_starts = $_SESSION['form_data']['dur_between_starts'] ?? "Not set";
        $video_dur = $_SESSION['form_data']['video_dur'] ?? "Not set";
        $video_delay = $_SESSION['form_data']['video_delay'] ?? "Not set";
        $num_video = $_SESSION['form_data']['num_video'] ?? 1;

        // Log to console
        console_log("First start time: $start_time");
        console_log("Video end duration: $video_end + 2 minutes after start");
        console_log("Number of starts: $num_starts");
        console_log("Duration between starts: $dur_between_starts");
        console_log("Video duration: $video_dur");
        console_log("Video delay after start: $video_delay");
        console_log("Number of videos during finish: $num_video");
    } else {
        console_log("No form data found in the session.");
    }
    ?>
</div>
<header>
    <div style="text-align: center;">
        <div class="w3-container w3-green">
            <h2>Regattastart9 with image detection </h2>
        </div>
    </div>
    <div style="text-align: center;">
        <?php
            echo "     Version: " . APP_VERSION . "<br><p></p>";
        ?>
    </div>
</header>
<!-- HTML form -->
<div class="w3-container" style="text-align: center;">
    <!-- Content Wrapper with center alignment -->
    <div class="w3-margin w3-padding-large content-wrapper">
        <form action="index9.php" method="POST">
            <div class="w3-row-padding">
                <!-- Left side content -->
                <div class="w3-half">
                    <div class="w3-pale-yellow" style="text-align: center;">
                        <fieldset>
                            <legend>Day and time setup: </legend>
                            <?php $day = date("l") ?>
                            <br>
                            Day for race <select name = "day" id="day">
                                <option <?php if(isset($day) && $day == "Monday"){echo "selected=\"selected\"";} ?> value="Monday">Monday</option>
                                <option <?php if(isset($day) && $day == "Tuesday"){echo "selected=\"selected\"";} ?> value="Tuesday">Tuesday</option>
                                <option <?php if(isset($day) && $day == "Wednesday"){echo "selected=\"selected\"";} ?> value="Wednesday">Wednesday</option>
                                <option <?php if(isset($day) && $day == "Thursday"){echo "selected=\"selected\"";} ?> value="Thursday">Thursday</option>
                                <option <?php if(isset($day) && $day == "Friday"){echo "selected=\"selected\"";} ?> value="Friday">Friday</option>
                                <option <?php if(isset($day) && $day == "Saturday"){echo "selected=\"selected\"";} ?> value="Saturday">Saturday</option>
                                <option <?php if(isset($day) && $day == "Sunday"){echo "selected=\"selected\"";} ?> value="Sunday">Sunday</option>
                            </select>
                            <p></p>
                            <div data-tap-disabled="true">
                            <?php 
                                // Set the correct time zone (adjust as needed)
                                date_default_timezone_set('Europe/Stockholm'); //your time zone

                                $start_time = isset($_SESSION["form_data"]["start_time"]) ? $_SESSION["form_data"]["start_time"] : "";
                                $steps = 5; // Interval in minutes
                                $loops = 24 * (60 / $steps); // Number of intervals in a day

                                // Get the current time and add 5 minutes
                                $current = time(); 
                                $adjusted_time = $current + (5 * 60);

                                // Calculate the nearest time in 5-minute intervals
                                $nearest_time = strtotime('today') + ceil(($adjusted_time - strtotime('today')) / (5 * 60)) * (5 * 60);

                                // Format the pre-selected option
                                $start_time_option = date('H:i', $nearest_time);
                            ?>
                            Start Time: <select name="start_time" id="start_time">
                                <?php
                                    // Loop through the intervals in a day starting from the nearest time
                                    for ($i = 0; $i < $loops; $i++) {
                                        // Calculate the time for this option
                                        $time_option = date('H:i', $nearest_time + ($i * $steps * 60));

                                        // Check if this option should be selected
                                        $selected = ($time_option == $start_time_option) ? "selected" : ""; 

                                        // Output the option tag
                                        echo '<option value="' . $time_option . '" ' . $selected . '>' . $time_option . '</option>';
                                    }
                                ?>
                            </select>
                            <br>
                            <p style="font-size:11px">
                            (First start in case of 2 starts)
                            <br>
                        </fieldset>
                    </div>
                </div>
                <!-- Right side content -->
                <div class="w3-half">
                    <div class="w3-pale-yellow" style="text-align: center;">
                        <fieldset>
                            <legend>Video Setup: </legend>
                            <p></p>
                            End for the finish video, duration from last start:
                            <select name = "video_end" id = "video_end">
                                // <option value="60" <?php if(isset($video_end) && $video_end == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
                                <option value="60" <?php if(isset($video_end) && $video_end == "60"){echo "selected=\"selected\"";} ?> value="60">60</option>
                                <option value="90" <?php if(isset($video_end) && $video_end == "90"){echo "selected=\"selected\"";} ?> value="90">90</option>
                                <option value="120" <?php if(isset($video_end) && $video_end == "120"){echo "selected=\"selected\"";} ?> value="120">120</option>
                                <option value="180" <?php {echo "selected=\"selected\"";} ?> value="180">180</option>
                                <option value="20" <?php if(isset($video_end) && $video_end == "20"){echo "selected=\"selected\"";} ?> value="20">20</option>
                            </select>
                            <br>
                            <p style="font-size:11px">
                            (Max duration of race)
                            <br>
                        </fieldset>
                    </div>
                </div>
            </div>
            <br>
            <!-- Central content below pale-yellow -->
            <div class="w3-row-padding">
                <div class="w3-round w3-light-grey w3-cell">
                    <fieldset>
                        <legend> Setup of number of starts 1..4 </legend>
                        <p></p>
                        Number of starts: <select name="num_starts" id="num_starts">
                            <option <?php if(isset($num_starts) && $num_starts == "1"){echo "selected=\"selected\"";} ?> value="1">1</option>
                            <option <?php if(isset($num_starts) && $num_starts == "2"){echo "selected=\"selected\"";} ?> value="2">2</option>
                            <option <?php if(isset($num_starts) && $num_starts == "3"){echo "selected=\"selected\"";} ?> value="3">3</option>
                            <option <?php if(isset($num_starts) && $num_starts == "4"){echo "selected=\"selected\"";} ?> value="4">4</option>
                        </select>
                        <p></p>
                        <!-- Option that should be hidden when only one start -->
                        <div id="secondOptionContainer" style="display: none;">
                            <span id="secondOptionText">In case of 2 starts, duration between the starts:</span>
                            <select name="dur_between_starts" id="dur_between_starts">
                                <option <?php if(isset($dur_between_starts) && $dur_between_starts == "5"){echo "selected=\"selected\"";} ?> value="5">5</option>
                                <option <?php if(isset($dur_between_starts) && $dur_between_starts == "10"){echo "selected=\"selected\"";} ?> value="10">10</option>
                            </select>
                        </div>
                    </fieldset>
                </div>
            </div>
            <div>
                <p>
            </div>
            <!-- Execute button, central below ligth-grey -->
            <div class="w3-row-padding">
                <div class="w3-round w3-blue w3-cell">
                    <fieldset>
                        <legend>Execute</legend>
                        <div id="submit" align="center"></div>
                            <div class="w3" align="center">
                                <button type="submit">Submit</button>
                            </div>
                    </fieldset>
                </div>
            </div>
        </form>
    </div>
</div>
<!-- Here is our page's main content -->
<main>
    <div id="result" align="center"></div>
        <div class="w3-container" align="center">
        <div class="w3-row-padding" style="text-align: center;">
            <div id="result" ></div>
        </div>
    <h5><a href="/index.php">  Resultat sida  </a></h5>
</main>
<footer>
    <div style="text-align: center;" class="w3-panel w3-grey">
        <?php
            // output when index9.php was last modified.
            $filename = 'index9.php';
            if (file_exists($filename)) {
                console_log( "This web-page: $filename was last modified: " . date ("Y-m-d H:i:s.", filemtime($filename)));
            }
        ?>
    </div>
    <div class="w3-row-padding" align="center">
        <br><p> - phwe - <br></p>
    </div>
</footer>
<!-- JavaScript to show/hide the second option based on the condition 1 or 2 starts -->
<script>
    // JavaScript to show/hide the second option based on the condition 1 or 2 starts
    document.addEventListener('DOMContentLoaded', function() {
        var numStarts = <?php echo json_encode($num_starts); ?>;
        var secondOptionContainer = document.getElementById('secondOptionContainer');
        toggleSecondOption(numStarts, secondOptionContainer);

        document.querySelector('select[name="num_starts"]').addEventListener('change', function(event) {
            var selectedValue = event.target.value;
            toggleSecondOption(selectedValue, secondOptionContainer);
        });
    });

    function toggleSecondOption(numStarts, containerElement) {
        if (numStarts == 1) {
            containerElement.style.display = 'none';
        } else {
            containerElement.style.display = 'block';
        }
    }
</script>
</body>
</html>
